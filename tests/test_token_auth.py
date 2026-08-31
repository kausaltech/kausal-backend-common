from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone

import pytest
from asgiref.sync import async_to_sync
from oauth2_provider.models import get_access_token_model, get_application_model

from kausal_common.asgi.middleware import GeneralRequestMiddleware, build_request_uri
from kausal_common.auth.tokens import authenticate_from_authorization_header

if TYPE_CHECKING:
    from kausal_common.asgi.types import ASGICommonScope

    from users.models import User

pytestmark = pytest.mark.django_db

RESOURCE_URI = 'https://example.com/mcp'
OTHER_RESOURCE_URI = 'https://example.com/some-other-api'


@pytest.fixture
def token_user() -> User:
    return get_user_model().objects.create_user(email='token-auth@example.com')


def create_access_token(user: User, resource: list[str]) -> str:
    """Issue an access token, optionally bound to RFC 8707 resource indicators."""
    application_model = get_application_model()
    application = application_model.objects.create(
        name='Test client',
        client_type=application_model.CLIENT_CONFIDENTIAL,
        authorization_grant_type=application_model.GRANT_AUTHORIZATION_CODE,
        redirect_uris='https://example.com/callback',
    )
    token = str(uuid4())
    get_access_token_model().objects.create(
        user=user,
        application=application,
        token=token,
        scope='openid profile email',
        expires=timezone.now() + timedelta(hours=1),
        resource=resource,
    )
    return token


def make_scope(**overrides) -> ASGICommonScope:
    scope = {
        'type': 'http',
        'method': 'POST',
        'scheme': 'https',
        'path': '/mcp',
        'root_path': '',
        'headers': [(b'host', b'example.com')],
        'server': ('10.0.0.1', 8000),
    }
    scope.update(overrides)
    return cast('ASGICommonScope', scope)


def call_middleware(scope: ASGICommonScope, token: str) -> ASGICommonScope:
    """Run `GeneralRequestMiddleware` over a scope and return the scope its inner app saw."""
    seen: dict = {}

    async def inner(inner_scope, receive, send):
        seen.update(inner_scope)

    authenticated = cast(
        'ASGICommonScope',
        {**scope, 'headers': [*scope['headers'], (b'authorization', f'Bearer {token}'.encode())]},
    )
    async_to_sync(GeneralRequestMiddleware(inner))(authenticated, None, None)
    return cast('ASGICommonScope', seen)


def test_unrestricted_token_authenticates_without_a_request_uri(token_user: User):
    token = create_access_token(token_user, resource=[])

    ret = authenticate_from_authorization_header(f'Bearer {token}', 'graphql')

    assert ret.error is None
    assert ret.user == token_user


def test_resource_bound_token_authenticates_for_its_own_resource(token_user: User):
    token = create_access_token(token_user, resource=[RESOURCE_URI])

    ret = authenticate_from_authorization_header(f'Bearer {token}', 'graphql', request_uri=RESOURCE_URI)

    assert ret.error is None
    assert ret.user == token_user


def test_resource_bound_token_is_rejected_for_another_resource(token_user: User):
    token = create_access_token(token_user, resource=[RESOURCE_URI])

    ret = authenticate_from_authorization_header(f'Bearer {token}', 'graphql', request_uri=OTHER_RESOURCE_URI)

    assert ret.user is None
    assert ret.error is not None
    assert ret.error.id == 'invalid_token'


def test_build_request_uri_uses_the_host_header():
    assert build_request_uri(make_scope()) == RESOURCE_URI


def test_build_request_uri_includes_the_root_path():
    assert build_request_uri(make_scope(root_path='/api')) == 'https://example.com/api/mcp'


def test_build_request_uri_falls_back_to_the_server_address():
    scope = make_scope(headers=[], scheme='http')

    assert build_request_uri(scope) == 'http://10.0.0.1:8000/mcp'


def test_build_request_uri_omits_a_default_port():
    scope = make_scope(headers=[], server=('10.0.0.1', 443))

    assert build_request_uri(scope) == 'https://10.0.0.1/mcp'


def test_build_request_uri_is_empty_without_a_host():
    assert build_request_uri(make_scope(headers=[], server=None)) == ''


def test_middleware_authenticates_a_token_bound_to_the_requested_resource(token_user: User):
    token = create_access_token(token_user, resource=[RESOURCE_URI])

    scope = call_middleware(make_scope(), token)

    assert scope['user'] == token_user


def test_middleware_rejects_a_token_bound_to_another_resource(token_user: User):
    token = create_access_token(token_user, resource=[OTHER_RESOURCE_URI])

    scope = call_middleware(make_scope(), token)

    assert scope.get('user') is None
