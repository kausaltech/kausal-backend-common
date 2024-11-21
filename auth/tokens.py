from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Literal, cast

from oauth2_provider.views.oidc import InvalidJWSObject

if TYPE_CHECKING:
    from typing import type_check_only

    from django.http.request import HttpRequest
    from rest_framework.authentication import TokenAuthentication
    from rest_framework.request import Request

    from oauth2_provider.contrib.rest_framework import OAuth2Authentication


@cache
def get_id_token_authenticator() -> type[TokenAuthentication] | None:
    try:
        from kausal_paths_extensions.auth.authentication import (  # type: ignore[import-not-found]
            IDTokenAuthentication,
        )
    except ImportError:
        pass
    else:
        return IDTokenAuthentication
    try:
        from kausal_watch_extensions.auth.authentication import IDTokenAuthentication  # type: ignore[import-not-found, no-redef]
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
    try:
        from kausal_paths_extensions.auth.authentication import (
            AccessTokenAuthentication as PathsAccessTokenAuth,  # type: ignore[missing-imports]
        )
    except ImportError:
        pass
    else:
        return cast('type[AccessTokenAuthentication]', PathsAccessTokenAuth)
    try:
        from kausal_paths_extensions.auth.authentication import (
            AccessTokenAuthentication as WatchAccessTokenAuth,  # type: ignore[missing-imports]
        )
    except ImportError:
        pass
    else:
        return cast('type[AccessTokenAuthentication]', WatchAccessTokenAuth)
    return None


def authenticate_api_request(request: HttpRequest, api_type: Literal['graphql', 'rest-api']) -> dict[str, str] | None:
    if 'authorization' not in request.headers:
        return None
    id_token_auth = get_id_token_authenticator()
    if id_token_auth is not None:
        auth = id_token_auth()
        try:
            ret = auth.authenticate(cast('Request', request))
        except InvalidJWSObject:
            ret = None
        if ret is not None:
            request.user = ret[0]
            return None

    access_token_auth = get_access_token_authenticator()
    if access_token_auth is not None:
        auth = access_token_auth(api_type)
        ret = auth.authenticate(cast('Request', request))
        if ret is not None:
            request.user = ret[0]
            return None
        err = getattr(request, 'oauth2_error', None)
        if err is not None:
            for key, val in list(err.items()):
                if val is None:
                    continue
                err[key] = str(val)
            return err
    return None
