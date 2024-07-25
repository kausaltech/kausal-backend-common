from typing import ClassVar, Self, TypeVar
from django.db.models import Model, QuerySet, Manager
from django.db import models
from treebeard.models import Node as Node



class MP_NodeManager[M: MP_Node](models.Manager[M]): ...


#M = TypeVar('M', bound=MP_Node, infer_variance=True)
#QS = TypeVar('QS', bound=QuerySet[Model], default=QuerySet[M], covariant=True)

class MP_NodeQuerySet[M: MP_Node](QuerySet[M]): ...

class MP_Node[M: MP_Node, QS: MP_NodeQuerySet](Node[M, QS]):
    steplen: int
    alphabet: str
    node_order_by: list[str]
    path: models.CharField
    depth: int
    numchild: models.PositiveBigIntegerField
    gap: int

    objects: ClassVar[MP_NodeManager]

    def get_children(self) -> QS: ...
