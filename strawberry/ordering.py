"""Shared Strawberry helpers for ordered model types and inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry as sb
from strawberry import Maybe

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence


@sb.input
class SiblingPositionInputMixin:
    """Mixin for mutation inputs that support sibling-relative positioning."""

    previous_sibling: Maybe[sb.ID]
    next_sibling: Maybe[sb.ID]


def with_sibling_ids[T](
    items: Sequence[T],
    get_id: Callable[[T], sb.ID],
) -> Iterator[tuple[T, sb.ID | None, sb.ID | None]]:
    """
    Yield (item, previous_sibling_id, next_sibling_id) for each item in an ordered sequence.

    Use this when building query-type lists to populate sibling navigation fields.
    """
    for i, item in enumerate(items):
        prev_id = get_id(items[i - 1]) if i > 0 else None
        next_id = get_id(items[i + 1]) if i < len(items) - 1 else None
        yield item, prev_id, next_id
