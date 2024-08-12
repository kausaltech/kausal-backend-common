from typing import Any

from django.db.models import Model
from django.db.models.fields.related import ForeignKey, ManyToManyDescriptor, ManyToManyField
from typing_extensions import TypeVar

_M = TypeVar('_M', bound=Model)
_Through = TypeVar('_Through', bound=Model, default=Any)

_ST = TypeVar("_ST")
# __get__ return type
_GT = TypeVar("_GT", default=_ST)


class ParentalKey(ForeignKey[_ST, _GT]): ...  # pyright: ignore

type PK[M: Model] = ParentalKey[M, M]

class ParentalManyToManyField(ManyToManyField[_M, _Through]):
    ...

type PM2M[M: Model] = ParentalKey[M, M]


class ParentalManyToManyDescriptor(ManyToManyDescriptor[_M, _Through]):  # type: ignore[type-var]
    ...
