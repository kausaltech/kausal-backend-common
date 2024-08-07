from typing import Any, Callable, Sequence, Type, TypeAlias, TypeVar, Union

from django.db.models import Prefetch

class noop: ...

F = TypeVar('F', bound=Callable)

type SelectRelatedVal = str
type SelectRelated = SelectRelatedVal | Callable[[Any], str]
type PrefetchRelatedVal = str | Prefetch
type PrefetchRelated = PrefetchRelatedVal | Callable[[Any], PrefetchRelatedVal]


def resolver_hints(
    model_field: str | Sequence[str] | None = None,
    select_related: SelectRelated | Sequence[SelectRelated] | type[noop] = ...,
    prefetch_related: PrefetchRelated | Sequence[PrefetchRelated] | type[noop] = ...,
    only: Sequence[str] | type[noop] = ...,
) -> Callable[[F], F]: ...
