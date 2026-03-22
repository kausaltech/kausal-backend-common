from typing import TypeVar

from graphene import Field

T = TypeVar('T', bound=Field)

def field[T: Field](field_type: T, *args, **kwargs) -> T: ...
