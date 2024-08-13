from typing import ClassVar, TypeVar

from django.db import models
from django.db.models import QuerySet

from treebeard.models import Node as Node

class MP_NodeQuerySet[M: MP_Node](QuerySet[M]): ...  # noqa: N801


class MP_NodeManager[M: MP_Node](models.Manager[M]): ...  # noqa: N801  # noqa: N801


_MPN_Mgr = TypeVar('_MPN_Mgr', bound=MP_NodeManager, covariant=True)  # noqa: PLC0105


class MP_Node[QS: MP_NodeQuerySet](Node[QS]):  # noqa: N801
    steplen: int
    alphabet: str
    node_order_by: list[str]
    path: models.CharField[str, str]
    depth: int
    numchild: models.PositiveBigIntegerField
    gap: int

    objects: ClassVar[_MPN_Mgr]  # type: ignore

    @classmethod
    def _get_basepath(cls, path: str, depth: int) -> str: ...
