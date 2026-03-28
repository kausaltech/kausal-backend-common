from typing import TypeVar

from graphene import Field

T = TypeVar('T', bound=Field)  # noqa: PYI001 type stubs

def field[T: Field](field_type: T, *args, **kwargs) -> T: ...
