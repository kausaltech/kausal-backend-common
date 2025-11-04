from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, cast

import graphene

if TYPE_CHECKING:
    from graphene.types.base import BaseOptions

type RegistrableType = type[graphene.ObjectType[Any] | graphene.Interface[Any]]

class GrapheneRegistry:
    types: OrderedDict[str, RegistrableType]

    def __init__(self) -> None:
        self.types = OrderedDict()

    def register(self, cls: RegistrableType) -> RegistrableType:
        meta = cast('BaseOptions', cls._meta)  # type: ignore[union-attr]  # pyright: ignore[reportAttributeAccessIssue]
        if meta.name in self.types:
            raise ValueError(f"Type {cls.__name__} already registered")
        self.types[meta.name] = cls
        return cls

    def get_list(self) -> list[RegistrableType]:
        return list(self.types.values())

registry = GrapheneRegistry()


def register_graphene_node[OT: graphene.ObjectType[Any]](cls: type[OT]) -> type[OT]:
    registry.register(cls)
    return cls


def register_graphene_interface[IT: graphene.Interface[Any]](cls: type[IT]) -> type[IT]:
    registry.register(cls)
    return cls
