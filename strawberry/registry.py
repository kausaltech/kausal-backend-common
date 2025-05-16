from __future__ import annotations

from typing import TYPE_CHECKING, cast, overload

from strawberry.types import has_object_definition

if TYPE_CHECKING:
    from collections.abc import Callable

strawberry_types: set[type] = set()

@overload
def register_strawberry_type[T: type](t: T) -> T: ...

@overload
def register_strawberry_type[T: type]() -> Callable[[T], T]: ...


def register_strawberry_type[T: type](t: T | None = None) -> T | Callable[[T], T]:
    def wrapper(type_: T) -> T:
        if not has_object_definition(type_):
            raise TypeError(f"Type {type_} is not a Strawberry type")
        if type_ in strawberry_types:
            raise ValueError(f"Type {type_} is already registered")
        strawberry_types.add(type_)
        return cast('T', type_)

    return wrapper if t is None else wrapper(t)
