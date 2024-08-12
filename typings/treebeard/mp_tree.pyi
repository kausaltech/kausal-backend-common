from typing import ClassVar

from django.db import models
from django.db.models import QuerySet
from treebeard.models import Node as Node

class MP_NodeManager[M: MP_Node](models.Manager[M]): ...  # noqa: N801


class MP_NodeQuerySet[M: MP_Node](QuerySet[M]): ...  # noqa: N801

class MP_Node[M: MP_Node, QS: MP_NodeQuerySet](Node[M, QS]):  # noqa: N801
    steplen: int
    alphabet: str
    node_order_by: list[str]
    path: models.CharField
    depth: int
    numchild: models.PositiveBigIntegerField
    gap: int

    objects: ClassVar[MP_NodeManager]

    def get_children(self) -> QS: ...
