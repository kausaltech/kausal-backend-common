from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Self

from django.core import checks
from django.db import models
from django.utils.translation import pgettext_lazy

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from django.core.checks import CheckMessage


class OrderedModel(models.Model):  # noqa: DJ008
    """Like wagtailorderable.models.Orderable, but with additional functionality in filter_siblings()."""

    order = models.PositiveIntegerField(
        default=0,
        editable=True,
        verbose_name=pgettext_lazy('integer to specify the sorting order of model instances', 'order'),
    )
    sort_order_field = 'order'
    order_on_create: int | None

    # Non-DB attributes for sibling-relative positioning.
    # Set these before calling finalize_sibling_order().
    previous_sibling: UUID | None = None
    next_sibling: UUID | None = None

    if TYPE_CHECKING:
        Meta: Any
    else:

        class Meta:
            abstract = True

    def __init__(self, *args, order_on_create: int | None = None, **kwargs):
        # Specify `order_on_create` to set the order to that value when saving if the instance is being created. If it is
        # None, the order will instead be set to <maximum existing order> + 1.
        super().__init__(*args, **kwargs)
        self.order_on_create = order_on_create

    def save(self, *args, **kwargs):
        if self.pk is None:
            order_on_create = getattr(self, 'order_on_create', None)
            if order_on_create is not None:
                self.order = order_on_create
            else:
                self.order = self.get_sort_order_max() + 1
        super().save(*args, **kwargs)

    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]:
        errors = super().check(**kwargs)
        if getattr(cls.filter_siblings, '__isabstractmethod__', False):
            errors.append(checks.Warning('filter_siblings() not defined', hint='Implement filter_siblings() method', obj=cls))
        return errors

    # Probably for compatibility with things that expect a `sort_order` field as in wagtailorderable.models.Orderable
    @property
    def sort_order(self):
        return self.order

    @abc.abstractmethod
    def filter_siblings(self, qs: models.QuerySet[Self]) -> models.QuerySet[Self]:
        raise NotImplementedError('Implement in subclass')

    def get_sort_order_max(self):
        """
        Get the max sort_order when a new instance is created.

        If you order depends on a FK (eg. order of books for a specific author),
        you can override this method to filter on the FK.
        ```
        def get_sort_order_max(self):
            qs = self.__class__.objects.filter(author=self.author)
            return qs.aggregate(Max(self.sort_order_field))['sort_order__max'] or 0
        ```
        """
        qs = self.__class__.objects.all()  # type: ignore
        if not getattr(self.filter_siblings, '__isabstractmethod__', False):
            qs = self.filter_siblings(qs)

        return qs.aggregate(models.Max(self.sort_order_field))['%s__max' % self.sort_order_field] or 0

    @classmethod
    def finalize_sibling_order(
        cls: type[Self],
        siblings_qs: models.QuerySet[Self],
        hinted: Sequence[Self] = (),
    ) -> None:
        """
        Recompute ordering for siblings, applying sibling-relative hints.

        Call this inside a transaction after all creates/updates are done.
        Instances in `hinted` may have `previous_sibling` or `next_sibling`
        set (as UUIDs). The method:

        1. Fetches all siblings from the DB (baseline order).
        2. For each hinted instance (in list order), removes it from its
           current position and re-inserts it relative to the referenced
           sibling.
        3. Bulk-updates only the rows whose order value changed.

        Requires that the model also inherits from UUIDIdentifiedModel.
        """
        _check_has_uuid(cls)

        all_siblings = _load_siblings(siblings_qs)
        by_uuid: dict[UUID, _SiblingInfo] = {s.uuid: s for s in all_siblings}
        order_list: list[UUID] = [s.uuid for s in all_siblings]

        _apply_hints(order_list, hinted, by_uuid)
        _bulk_update_order(siblings_qs, order_list, by_uuid)


class _SiblingInfo:
    """Lightweight container for sibling PK, UUID, and current order."""

    __slots__ = ('order', 'pk', 'uuid')

    def __init__(self, pk: int, uuid: UUID, order: int) -> None:
        self.pk = pk
        self.uuid = uuid
        self.order = order


def _get_uuid(instance: OrderedModel) -> UUID:
    """Get UUID from an instance, assuming it also inherits UUIDIdentifiedModel."""
    return instance.uuid  # type: ignore[attr-defined]


def _check_has_uuid(cls: type) -> None:
    from kausal_common.models.uuid import UUIDIdentifiedModel

    if not issubclass(cls, UUIDIdentifiedModel):
        raise TypeError(f'{cls.__name__} must inherit from UUIDIdentifiedModel to use finalize_sibling_order')


def _load_siblings[T: OrderedModel](siblings_qs: models.QuerySet[T]) -> list[_SiblingInfo]:
    return [
        _SiblingInfo(pk=pk, uuid=uuid, order=order)
        for pk, uuid, order in siblings_qs.order_by('order', 'pk').values_list('pk', 'uuid', 'order')
    ]


def _apply_hints(
    order_list: list[UUID],
    hinted: Sequence[OrderedModel],
    by_uuid: dict[UUID, _SiblingInfo],
) -> None:
    """Apply sibling-relative hints to mutate order_list in place."""
    for item in hinted:
        if item.previous_sibling is not None and item.next_sibling is not None:
            raise ValueError(f'Item {_get_uuid(item)} has both previous_sibling and next_sibling set')
        if item.previous_sibling is None and item.next_sibling is None:
            continue

        item_uuid = _get_uuid(item)
        if item_uuid in order_list:
            order_list.remove(item_uuid)

        ref_uuid = item.previous_sibling if item.previous_sibling is not None else item.next_sibling
        assert ref_uuid is not None
        if ref_uuid not in by_uuid and ref_uuid not in {_get_uuid(h) for h in hinted}:
            raise ValueError(f'Sibling {ref_uuid} not found')

        try:
            ref_idx = order_list.index(ref_uuid)
        except ValueError:
            raise ValueError(f'Sibling {ref_uuid} not found in current ordering') from None

        insert_idx = ref_idx + 1 if item.previous_sibling is not None else ref_idx
        order_list.insert(insert_idx, item_uuid)


def _bulk_update_order(
    siblings_qs: models.QuerySet[OrderedModel],
    order_list: list[UUID],
    by_uuid: dict[UUID, _SiblingInfo],
) -> None:
    """Issue a single UPDATE for rows whose order value changed."""
    to_update: list[tuple[int, int]] = []
    for new_order, uuid in enumerate(order_list):
        sib = by_uuid.get(uuid)
        if sib is not None and sib.order != new_order:
            to_update.append((sib.pk, new_order))

    if not to_update:
        return

    whens = [models.When(pk=pk, then=models.Value(new_order)) for pk, new_order in to_update]
    pks = [pk for pk, _ in to_update]
    siblings_qs.filter(pk__in=pks).update(
        order=models.Case(*whens, output_field=models.PositiveIntegerField()),
    )
