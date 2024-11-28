from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from django.db.models import Model, Q

from kausal_common.models.permissions import PermissionedQuerySet

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from kausal_common.models.permission_policy import ObjectSpecificAction
    from kausal_common.users import UserOrAnon


class CacheableModel[CacheT](Model):
    class Meta:
        abstract = True

    @property
    def cache(self) -> CacheT:
        return getattr(self, '_cache')  # noqa: B009

    @cache.setter
    def cache(self, value: CacheT) -> None:
        setattr(self, '_cache', value)  # noqa: B010

    def has_cache(self) -> bool:
        return hasattr(self, '_cache')


@dataclass
class ModelObjectCache[ModelT: CacheableModel, QS: PermissionedQuerySet[Any], ParentM: CacheableModel | None](ABC):
    parent: ParentM
    user: UserOrAnon | None
    _by_id: dict[int, ModelT] = field(init=False, default_factory=dict)
    _is_fully_prefetched: bool = field(init=False, default=False)
    _groups: dict[str, ObjectCacheGroup[ModelT]] = field(init=False, default_factory=dict)

    @property
    @abstractmethod
    def model(self) -> type[ModelT]: ...

    def __post_init__(self) -> None:
        return

    def populate(self, qs: QS) -> Iterable[ModelT]:
        """Populate the object cache."""

        obj_list = self._as_list(qs)
        for obj in obj_list:
            self.add_obj(obj)
        return obj_list

    def add_obj(self, obj: ModelT) -> None:
        """Add an object to cache."""

        for grp in self._groups.values():
            grp.add(obj)

    def get_list_by_group(self, group_type: str, group_id: int) -> list[ModelT]:
        return self._groups[group_type].get_list(group_id)

    def get_base_qs(self, qs: QS | None = None, action: ObjectSpecificAction = 'view'):
        if qs is None:
            qs = cast(QS, self.model._default_manager.get_queryset())
        if self.parent is not None:
            qs = self.filter_by_parent(qs)
        qs = self.filter_for_user(qs, action)
        return qs

    def _as_list(self, qs: QS) -> list[ModelT]:
        return list(qs)

    def filter_for_user(self, qs: QS, action: ObjectSpecificAction = 'view') -> QS:
        if self.user is None:
            return qs
        if action == 'view':
            return qs.viewable_by(self.user)
        if action == 'change':
            return qs.modifiable_by(self.user)
        if action == 'delete':
            return qs.deletable_by(self.user)
        raise KeyError("Invalid action: %s" % action)

    def filter_by_parent(self, qs: QS) -> QS:
        return qs

    def _do_populate(self, qs_filter: Q | None = None) -> list[ModelT]:
        qs = self.get_base_qs()
        if qs_filter is not None:
            qs = qs.filter(qs_filter)
        objs: list[ModelT] = []
        for obj in self.populate(qs):
            self._by_id[obj.pk] = obj
            objs.append(obj)
        return objs

    def full_populate(self):
        if self._is_fully_prefetched:
            return
        self._do_populate()
        self._is_fully_prefetched = True

    def get_list(self, filter_func: Callable[[ModelT], bool] | None = None) -> list[ModelT]:
        self.full_populate()
        obj_list = list(self._by_id.values())
        if filter_func:
            return list(filter(filter_func, obj_list))
        return obj_list

    def get(self, obj_id: int, qs_filter: Q | None = None) -> ModelT | None:
        if obj_id in self._by_id:
            return self._by_id[obj_id]
        self._do_populate(qs_filter)
        return self._by_id.get(obj_id)

    def get_by_q(self, q: Q) -> ModelT | None:
        objs = self._do_populate(q)
        if len(objs) == 0:
            return None
        if len(objs) > 1:
            raise ValueError("Multiple objects found for query: %s" % q)
        return objs[0]

    def first(self, qs_filter: Q) -> ModelT | None:
        obj_list = self._do_populate(qs_filter)
        if len(obj_list) == 0:
            return None
        return obj_list[0]


@dataclass
class ObjectCacheGroup[CachedM: CacheableModel]:
    cache: ModelObjectCache[Any, Any, Any]
    get_group: Callable[[CachedM], int]
    objs: dict[int, dict[int, CachedM]] = field(init=False, default_factory=dict)

    def add(self, obj: CachedM):
        group_id = self.get_group(obj)
        group_objs = self.objs.setdefault(group_id, {})
        if obj.pk not in group_objs:
            group_objs[obj.pk] = obj

    def get_list(self, group_id: int) -> list[CachedM]:
        self.cache.full_populate()
        group_objs = list(self.objs.get(group_id, {}).values())
        return group_objs
