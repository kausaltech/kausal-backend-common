from typing import ClassVar, Self, TypeVar
from django.db.models import Model, QuerySet
from django.db import models
from treebeard.models import Node as Node


class MP_NodeManager(models.Manager[M]): ...


M = TypeVar('M', bound=Model, default=Model)
QS = TypeVar('QS', bound=QuerySet[Model], default=QuerySet[M])  # pyright: ignore

class MP_Node(Node[M, QS]):  # type: ignore[django-manager-missing]
    steplen: int
    alphabet: str
    node_order_by: list[str]
    path: models.CharField
    depth: models.PositiveIntegerField
    numchild: models.PositiveBigIntegerField
    gap: int

    def get_children(self) -> QS: ...
