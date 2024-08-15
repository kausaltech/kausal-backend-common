from typing_extensions import TypeVar

from django.db.models import Manager, Model, QuerySet

_M = TypeVar('_M', bound=Model, covariant=True)

class MultilingualQuerySet(QuerySet[_M, _M]): ...
class MultilingualManager(Manager[_M]): ...
