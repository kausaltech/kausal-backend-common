# ruff: noqa: N801
from typing import Any, Self

from django.db import models
from django.db.models import Manager, Model, QuerySet

from treebeard.models import Node as Node

class MP_NodeQuerySet[M: Model](QuerySet[M, M]):
    def delete(self, *args, **kwargs): ...


class MP_NodeManager[M: Model](Manager[M]): ...


class MP_Node[QS: QuerySet[Any] = QuerySet[Any]](Node[QS]):
    steplen: int
    alphabet: str
    node_order_by: list[str]
    path: models.CharField[str, str]
    depth: int
    numchild: models.PositiveBigIntegerField[int, int]
    gap: int

    @classmethod
    def _get_basepath(cls, path: str, depth: int) -> str: ...

    def get_descendants(self) -> QS: ...
    def get_children(self) -> QS: ...
    def get_parent(self, update: bool = ...) -> Self | None: ...
