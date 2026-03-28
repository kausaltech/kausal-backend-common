from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from django.db.models import Prefetch

class noop: ...  # noqa: N801 type stubs

F = TypeVar('F', bound=Callable)  # noqa: PYI001 type stubs

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
