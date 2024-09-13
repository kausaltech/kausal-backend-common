from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Self

from django.core import checks
from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.core.checks import CheckMessage


class OrderedModel(models.Model):
    """Like wagtailorderable.models.Orderable, but with additional functionality in filter_siblings()."""

    order = models.PositiveIntegerField(default=0, editable=True, verbose_name=_('order'))
    sort_order_field = 'order'
    order_on_create: int | None

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is None:
            order_on_create = getattr(self, 'order_on_create', None)
            if order_on_create is not None:
                self.order = order_on_create
            else:
                self.order = self.get_sort_order_max() + 1
        super().save(*args, **kwargs)

    def __init__(self, *args, order_on_create: int | None = None, **kwargs):
        # Specify `order_on_create` to set the order to that value when saving if the instance is being created. If it is
        # None, the order will instead be set to <maximum existing order> + 1.
        super().__init__(*args, **kwargs)
        self.order_on_create = order_on_create

    @classmethod
    def check(cls, **kwargs) -> list[CheckMessage]:
        errors = super().check(**kwargs)
        if getattr(cls.filter_siblings, '__isabstractmethod__', False):
            errors.append(checks.Warning("filter_siblings() not defined", hint="Implement filter_siblings() method", obj=cls))
        return errors

    # Probably for compatibility with things that expect a `sort_order` field as in wagtailorderable.models.Orderable
    @property
    def sort_order(self):
        return self.order

    @abc.abstractmethod
    def filter_siblings(self, qs: models.QuerySet[Self]) -> models.QuerySet[Self]:
        raise NotImplementedError("Implement in subclass")

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
