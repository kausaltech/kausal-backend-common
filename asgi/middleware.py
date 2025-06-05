from __future__ import annotations

from typing import TYPE_CHECKING

from channels.auth import AuthMiddlewareStack
from channels.db import sync_to_async
from channels.middleware import BaseMiddleware
from channels.security.websocket import AllowedHostsOriginValidator
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from kausal_common.auth.tokens import authenticate_from_authorization_header
from kausal_common.logging.request import RequestCommonMeta

if TYPE_CHECKING:
    from uvicorn._types import ASGIApplication

    from kausal_common.asgi.types import ASGICommonScope


class GeneralRequestMiddleware(BaseMiddleware):
    """General request middleware that performs token auth and log context setup."""

    async def __call__(self, scope: ASGICommonScope, receive, send):
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
            return await super().__call__(scope, receive, send)


def HTTPMiddleware(inner: ASGIApplication) -> ASGIApplication:  # noqa: N802
    return SentryAsgiMiddleware(
        ProxyHeadersMiddleware(
            AuthMiddlewareStack(
                GeneralRequestMiddleware(inner)
            ),
            trusted_hosts='*'
        ),
    )


def WebSocketMiddleware(inner: ASGIApplication) -> ASGIApplication:  # noqa: N802
    return SentryAsgiMiddleware(
        ProxyHeadersMiddleware(
            AllowedHostsOriginValidator(
                AuthMiddlewareStack(GeneralRequestMiddleware(inner))
            ),
            trusted_hosts='*'
        ),
    )
