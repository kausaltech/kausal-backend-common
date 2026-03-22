from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.contrib.sessions.backends.base import SessionBase

    from sentry_sdk import Scope as SentryScope

    from kausal_common.auth.tokens import TokenAuthResult

    from users.models import User


class ASGICommonScope(TypedDict):
    type: Literal['http', 'websocket']
    http_version: str
    method: str
    scheme: str
    path: str
    raw_path: bytes
    query_string: bytes
    root_path: str
    headers: Iterable[tuple[bytes, bytes]]
    client: tuple[str, int] | None
    server: tuple[str, int | None] | None
    state: NotRequired[dict[str, Any]]
    extensions: NotRequired[dict[str, dict[object, object]]]
    session: NotRequired[SessionBase | None]
    correlation_id: NotRequired[str | None]
    user: NotRequired[User | None]
    token_auth: NotRequired[TokenAuthResult | None]
    sentry_scope: NotRequired[SentryScope | None]
