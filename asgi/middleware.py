from __future__ import annotations

from typing import TYPE_CHECKING, cast

from channels.auth import AuthMiddlewareStack
from channels.db import sync_to_async  # pyright: ignore[reportAttributeAccessIssue]
from channels.middleware import BaseMiddleware
from channels.security.websocket import AllowedHostsOriginValidator
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from kausal_common.auth.tokens import authenticate_from_authorization_header

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from asgiref.typing import ASGIReceiveCallable, ASGISendCallable, Scope as ASGIScope
    from channels.consumer import _ASGIApplicationProtocol
    from starlette.types import ASGIApp as StarletteASGIApp
    from uvicorn._types import ASGIApplication as UvicornASGIApplication

    from kausal_common.asgi.types import ASGICommonScope

    type ASGIAppCallable = Callable[[ASGIScope, ASGIReceiveCallable, ASGISendCallable], Awaitable[None]]
    type ASGIApplication = UvicornASGIApplication | _ASGIApplicationProtocol | StarletteASGIApp | ASGIAppCallable

class GeneralRequestMiddleware(BaseMiddleware):
    """General request middleware that performs token auth and log context setup."""

    async def __call__(self, scope: ASGICommonScope, receive, send):
        from kausal_common.logging.request import RequestCommonMeta

        headers = dict(scope['headers'])
        auth_header = headers.get(b'authorization')
        if auth_header:
            token = auth_header.decode('utf-8')
            ret = await sync_to_async(authenticate_from_authorization_header)(token, 'graphql')
            scope['token_auth'] = ret
            if ret.user:
                scope['user'] = ret.user

        rc_meta = RequestCommonMeta.from_scope(scope)
        with rc_meta.start_request(scope=scope) as sentry_scope:
            _rich_traceback_omit = True
            scope['sentry_scope'] = sentry_scope
            return await super().__call__(scope, receive, send)  # pyright: ignore[reportArgumentType]


def HTTPMiddleware(inner: ASGIApplication) -> ASGIApplication:  # noqa: N802
    from django.conf import settings

    from asgi_cors import asgi_cors  # type: ignore[import-untyped]

    return cast('ASGIApplication',SentryAsgiMiddleware(
        ProxyHeadersMiddleware(
            AuthMiddlewareStack(  # pyright: ignore[reportArgumentType]
                GeneralRequestMiddleware(
                    asgi_cors(inner, allow_all=True, headers=settings.CORS_ALLOW_HEADERS))
            ),
            trusted_hosts='*'
        ),
        asgi_version=3,
    ))


def WebSocketMiddleware(inner: ASGIApplication) -> ASGIApplication:  # noqa: N802
    return cast('ASGIApplication',SentryAsgiMiddleware(
        ProxyHeadersMiddleware(
            AllowedHostsOriginValidator(  # pyright: ignore[reportArgumentType]
                AuthMiddlewareStack(GeneralRequestMiddleware(inner))
            ),
            trusted_hosts='*'
        ),
        asgi_version=3,
    ))
