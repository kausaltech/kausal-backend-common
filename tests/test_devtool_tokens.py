"""Tests for devtool ID-token bearer authentication (kausal_common.auth.tokens)."""

import time
import uuid
from typing import Any

from django.contrib.auth import get_user_model

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from jwt.algorithms import RSAAlgorithm
from social_django.models import UserSocialAuth

from kausal_common.auth.backends import KausalDevtoolAuth
from kausal_common.auth.tokens import TokenAuthResult, authenticate_devtool_id_token

pytestmark = pytest.mark.django_db

ISSUER = 'https://kc.kausal.tech/realms/kausal'
CLIENT_ID = 'kausal-paths-devtool'
KID = 'devtool-test-key'
SUB = str(uuid.uuid4())

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _PRIVATE_KEY.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
_FOREIGN_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_FOREIGN_PEM = _FOREIGN_KEY.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())


def _jwk() -> dict[str, Any]:
    key = RSAAlgorithm.to_jwk(_PRIVATE_KEY.public_key(), as_dict=True)
    key.update({'kid': KID, 'alg': 'RS256', 'use': 'sig'})
    return key


def make_token(*, signing_pem: bytes = _PRIVATE_PEM, kid: str = KID, **claim_overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        'iss': ISSUER,
        'aud': CLIENT_ID,
        'azp': CLIENT_ID,
        'sub': SUB,
        'iat': now,
        'exp': now + 300,
    }
    claims.update(claim_overrides)
    return jwt.encode(claims, signing_pem, algorithm='RS256', headers={'kid': kid})


@pytest.fixture
def devtool_sso(settings, monkeypatch) -> None:
    settings.SOCIAL_AUTH_KAUSAL_DEVTOOL_OIDC_ENDPOINT = ISSUER
    settings.SOCIAL_AUTH_KAUSAL_DEVTOOL_KEY = CLIENT_ID
    settings.SOCIAL_AUTH_KAUSAL_DEVTOOL_ID_TOKEN_ISSUER = ISSUER
    monkeypatch.setattr(KausalDevtoolAuth, 'get_remote_jwks_keys', lambda _self: [_jwk()])


@pytest.fixture
def associated_user():
    user_model = get_user_model()
    user = user_model.objects.create(username='devtool-user', email='dev@kausal.tech')
    user.set_unusable_password()
    user.save()
    UserSocialAuth.objects.create(user=user, provider='kausal', uid=SUB)
    return user


def _auth(token: str) -> TokenAuthResult | None:
    return authenticate_devtool_id_token(f'Bearer {token}')


@pytest.mark.usefixtures('devtool_sso')
def test_valid_token_authenticates_associated_user(associated_user) -> None:
    result = _auth(make_token())

    assert result is not None
    assert result.error is None
    assert result.user == associated_user


@pytest.mark.usefixtures('devtool_sso')
def test_unassociated_sub_is_refused_without_creating_a_user() -> None:
    user_count = get_user_model().objects.count()

    result = _auth(make_token())

    assert result is not None
    assert result.user is None
    assert result.error is not None
    assert result.error.id == 'unknown_user'
    assert get_user_model().objects.count() == user_count


@pytest.mark.usefixtures('devtool_sso')
def test_inactive_user_is_refused(associated_user) -> None:
    associated_user.is_active = False
    associated_user.save()

    result = _auth(make_token())

    assert result is not None
    assert result.error is not None
    assert result.error.id == 'unknown_user'


@pytest.mark.usefixtures('devtool_sso', 'associated_user')
def test_wrong_audience_is_rejected() -> None:
    # A token minted for some other internal service must not authenticate here.
    result = _auth(make_token(aud='grafana', azp='grafana'))

    assert result is not None
    assert result.user is None
    assert result.error is not None
    assert result.error.id == 'invalid_token'


@pytest.mark.usefixtures('devtool_sso', 'associated_user')
def test_azp_mismatch_is_rejected() -> None:
    # Our audience present, but the token was authorized for another client.
    result = _auth(make_token(aud=[CLIENT_ID, 'kausal-paths'], azp='kausal-paths'))

    assert result is not None
    assert result.error is not None
    assert result.error.id == 'invalid_token'


@pytest.mark.usefixtures('devtool_sso', 'associated_user')
def test_expired_token_is_rejected() -> None:
    now = int(time.time())
    result = _auth(make_token(iat=now - 600, exp=now - 60))

    assert result is not None
    assert result.error is not None
    assert result.error.id == 'invalid_token'


@pytest.mark.usefixtures('devtool_sso', 'associated_user')
def test_stale_iat_is_rejected() -> None:
    # validate_temporal_claims enforces ID_TOKEN_MAX_AGE (600 s) freshness,
    # so clients must present recently minted tokens even if exp is generous.
    now = int(time.time())
    result = _auth(make_token(iat=now - 3600, exp=now + 300))

    assert result is not None
    assert result.error is not None
    assert result.error.id == 'invalid_token'


@pytest.mark.usefixtures('devtool_sso', 'associated_user')
def test_forged_signature_is_rejected() -> None:
    result = _auth(make_token(signing_pem=_FOREIGN_PEM))

    assert result is not None
    assert result.error is not None
    assert result.error.id == 'invalid_token'


@pytest.mark.usefixtures('devtool_sso')
def test_foreign_issuer_falls_through() -> None:
    assert _auth(make_token(iss='https://other-as.example/realm')) is None


@pytest.mark.usefixtures('devtool_sso')
def test_opaque_token_falls_through() -> None:
    assert _auth('an-opaque-oauth2-provider-token') is None


def test_unconfigured_deployment_falls_through(settings) -> None:
    settings.SOCIAL_AUTH_KAUSAL_DEVTOOL_OIDC_ENDPOINT = ''
    settings.SOCIAL_AUTH_KAUSAL_DEVTOOL_KEY = ''

    assert _auth(make_token()) is None


@pytest.mark.usefixtures('devtool_sso')
def test_authorization_header_entry_point_uses_devtool_path(associated_user) -> None:
    from kausal_common.auth.tokens import authenticate_from_authorization_header

    result = authenticate_from_authorization_header(f'Bearer {make_token()}', 'graphql')

    assert result.error is None
    assert result.user == associated_user
