from django.db.models import Manager, Model, QuerySet
from typing_extensions import TypeVar

_M = TypeVar('_M', bound=Model, covariant=True)  # noqa: PLC0105

class MultilingualQuerySet(QuerySet[_M, _M]): ...
class MultilingualManager(Manager[_M]): ...
