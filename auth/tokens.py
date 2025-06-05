from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Literal, cast

from loguru import logger

from kausal_common.const import IS_PATHS, IS_WATCH

if TYPE_CHECKING:
    from typing import type_check_only

    from django.http.request import HttpRequest
    from rest_framework.authentication import TokenAuthentication
    from rest_framework.request import Request

    from oauth2_provider.contrib.rest_framework import OAuth2Authentication
    from oauth2_provider.models import AccessToken, IDToken

    from kausal_common.deployment.types import LoggedHttpRequest

    from users.models import User


type TokenType = IDToken | AccessToken


@cache
def get_id_token_authenticator() -> type[TokenAuthentication] | None:
    if IS_PATHS:
        try:
            from kausal_paths_extensions.auth.authentication import (  # type: ignore[import-not-found]
                IDTokenAuthentication,
            )
        except ImportError:
            pass
        else:
            return IDTokenAuthentication
    if IS_WATCH:
        try:
            from kausal_watch_extensions.auth.authentication import IDTokenAuthentication  # type: ignore[import-not-found]
        except ImportError:
            pass
        else:
            return IDTokenAuthentication
    return None


if TYPE_CHECKING:
    @type_check_only
    class AccessTokenAuthentication(OAuth2Authentication):
        def __init__(self, realm: str) -> None: ...


@cache
def get_access_token_authenticator() -> type[AccessTokenAuthentication] | None:
    if IS_PATHS:
        try:
            from kausal_paths_extensions.auth.authentication import (
                AccessTokenAuthentication as PathsAccessTokenAuth,
            )
        except ImportError:
            pass
        else:
            return cast('type[AccessTokenAuthentication]', PathsAccessTokenAuth)
    if IS_WATCH:
        try:
            from kausal_watch_extensions.auth.authentication import (
                AccessTokenAuthentication as WatchAccessTokenAuth,
            )
        except ImportError:
            pass
        else:
            return cast('type[AccessTokenAuthentication]', WatchAccessTokenAuth)
    return None

@dataclass
class TokenAuthError:
    id: str
    description: str | None = None

    def __str__(self) -> str:
        if self.description:
            return f'{self.id}: {self.description}'
        return self.id

@dataclass
class TokenAuthResult:
    user: User | None = None
    token: TokenType | None = None
    error: TokenAuthError | None = None

    @property
    def token_type(self) -> Literal['id_token', 'access_token'] | None:
        if self.token is None:
            return None
        if 'IDToken' in self.token.__class__.__name__:
            return 'id_token'
        return 'access_token'

def authenticate_from_authorization_header(
    authorization: str, api_type: Literal['graphql', 'rest-api']
) -> TokenAuthResult:
    from oauth2_provider.oauth2_backends import get_oauthlib_core

    if TYPE_CHECKING:
        from oauth2_provider.oauth2_backends import OAuthLibCore
        from oauthlib.oauth2 import Server

    oauthlib_core: OAuthLibCore = get_oauthlib_core()
    server = cast('Server', oauthlib_core.server)
    valid, r = server.verify_request('', 'GET', body=None, headers=dict(
        Authorization=authorization,
    ), scopes=[])
    error_dict: dict[str, str] | None = getattr(r, 'oauth2_error', None) or None
    error: TokenAuthError | None = None
    if not valid:
        error = TokenAuthError(id='unknown', description='Unknown error')
        log_ctx = {}
        if error_dict:
            error.id = error_dict.get('error', 'unknown')
            error.description = error_dict.get('error_description')
            log_ctx['oauth2.error'] = error.id
            if error.description:
                log_ctx['oauth2.error_description'] = error.description
        logger.error('Invalid token: {error}', **log_ctx)
        return TokenAuthResult(error=error)

    token = cast('TokenType | None', r.access_token)
    return TokenAuthResult(user=cast('User', r.user), token=token)


def authenticate_api_request(request: HttpRequest, api_type: Literal['graphql', 'rest-api']) -> TokenAuthResult | None:
    if 'authorization' not in request.headers:
        return None
    request = cast('LoggedHttpRequest', request)
    id_token_auth = get_id_token_authenticator()
    if id_token_auth is not None:
        from oauth2_provider.views.oidc import InvalidJWSObject

        auth = id_token_auth()
        try:
            ret = auth.authenticate(cast('Request', request))
        except InvalidJWSObject:
            ret = None
        if ret is not None:
            request.user = ret[0]
            request.token_auth = TokenAuthResult(user=ret[0], token=ret[1])
            return request.token_auth

    access_token_auth = get_access_token_authenticator()
    if access_token_auth is None:
        return None
    auth = access_token_auth(api_type)
    ret = auth.authenticate(cast('Request', request))
    if ret is not None:
        request.user = ret[0]
        request.token_auth = TokenAuthResult(user=ret[0], token=ret[1])
        return request.token_auth
    oauth2_error = getattr(request, 'oauth2_error', None)
    if oauth2_error is None:
        return None

    error = TokenAuthError(id='unknown', description='Unknown error')
    if oauth2_error:
        error.id = oauth2_error.get('error', 'unknown')
        error.description = oauth2_error.get('error_description')
    return TokenAuthResult(error=error)
