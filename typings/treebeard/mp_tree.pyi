# ruff: noqa: N801
from typing import Generic, Self, TypeVar

from django.db import models
from django.db.models import Manager, Model, QuerySet

from treebeard.models import Node as Node

_Model = TypeVar("_Model", bound=Model, covariant=True)  # noqa: PLC0105

class MP_NodeQuerySet(QuerySet[_Model, _Model]):
    def delete(self, *args, **kwargs): ...

_MPN_QS = TypeVar('_MPN_QS', bound=QuerySet, default=QuerySet)

class MP_NodeManager(Manager[_Model]):
    def get_queryset(self) -> QuerySet: ...


class MP_Node(Generic[_MPN_QS], Node[_MPN_QS]):
    steplen: int
    alphabet: str
    node_order_by: list[str]
    path: models.CharField[str, str]
    depth: int
    numchild: models.PositiveBigIntegerField
    gap: int

    @classmethod
    def _get_basepath(cls, path: str, depth: int) -> str: ...

    def get_descendants(self) -> _MPN_QS: ...
    def get_children(self) -> _MPN_QS: ...
    def get_parent(self, update: bool = ...) -> Self | None: ...
