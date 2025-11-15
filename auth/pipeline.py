from __future__ import annotations

import hashlib
import io
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from wagtail.users.models import UserProfile

import sentry_sdk
from loguru import logger
from sentry_sdk import capture_exception
from social_core.backends.oauth import OAuthAuth
from social_core.backends.okta_openidconnect import OktaOpenIdConnect
from social_core.exceptions import AuthAlreadyAssociated, AuthForbidden

from kausal_common.auth.msgraph import get_user_photo_with_etag
from kausal_common.deployment import env_bool
from kausal_common.users.models import uuid_to_username

from users.models import User

if TYPE_CHECKING:
    from social_core.strategy import BaseStrategy
    from social_django import BaseAuth
    from social_django.models import UserSocialAuth

logger = logger.bind(name='auth.pipeline')


def log_login_attempt(
    backend: BaseAuth, response: dict[str, Any] | None = None, **_kwargs
):
    response = response or {}

    user_ctx: dict[str, str] = {}
    log_ctx: dict[str, str] = {
        'auth.backend': backend.name,
    }
    email = response.get('email')
    if email:
        user_ctx['email'] = email
    tid = response.get('tid')
    if tid:
        log_ctx['auth.tid'] = tid

    oid = response.get('oid')
    if oid:
        log_ctx['auth.oid'] = oid
        user_ctx['uuid'] = oid
    else:
        sub = response.get('sub')
        if sub:
            log_ctx['auth.sub'] = sub
            user_ctx['uuid'] = sub

    log = logger.bind(**log_ctx, **{'user.%s' % k: v for k, v in user_ctx.items()})
    log.info('Login attempt')
    if 'id_token' in response and env_bool('SSO_DEBUG_LOG', default=False):
        log.debug('ID token: %s' % response['id_token'])

    response_data = {key: val for key, val in response.items() if not key.endswith('token')}
    sentry_sdk.set_context('response', response_data)
    logger.info('Response data', **response_data)

    scope = sentry_sdk.get_isolation_scope()
    scope.set_user(user_ctx)

    if isinstance(backend, OAuthAuth):
        try:
            backend.validate_state()
        except Exception as e:
            logger.warning('Login failed with invalid state: %s' % str(e))


def get_username(details: dict[str, Any], backend: BaseAuth, response: dict[str, Any], **kwargs):
    """
    Set the `username` argument.

    If the user exists already, use the existing username. Otherwise
    generate username from the `new_uuid` using the
    `uuid_to_username` function.
    """
    if backend.name == 'password':
        return {'username': kwargs.get('uid')}

    user = details.get('user')
    if not user:
        user_uuid = kwargs.get('uid')
        if not user_uuid:
            return None
        try:
            user_uuid = UUID(user_uuid)
        except ValueError:
            user_uuid = None

        if user_uuid is None:
            user_uuid = response.get('sub')
            if not user_uuid:
                return None
        username = uuid_to_username(user_uuid)
    else:
        username = user.username

    return {
        'username': username,
    }


def associate_existing_social_user(backend: BaseAuth, uid: str, response: dict[str, Any], user: User | None = None, **kwargs):
    provider = backend.name
    social: UserSocialAuth | None = None
    social = backend.strategy.storage.user.get_social_auth(provider, uid)
    save_new_uid = False
    username = response.get('preferred_username')
    if social is None and isinstance(backend, OktaOpenIdConnect) and username and username != uid:
        # Okta OpenID Connect used to have the preferred_username as the unique identifier, so we check
        # for that too.
        social = cast('UserSocialAuth | None', backend.strategy.storage.user.get_social_auth(provider, username))
        if social is not None and uid != username:
            save_new_uid = True
    if social:
        if user and social.user != user:
            raise AuthAlreadyAssociated(backend)
        if not user:
            user = social.user
        elif save_new_uid:
            social.uid = uid
            social.save()

    return {
        "social": social,
        "user": user,
        "is_new": user is None,
        "new_association": social is None,
    }


def find_user_by_email(details: dict[str, Any], user: User | None = None, **_kwargs) -> dict[str, Any] | None:
    if user is not None:
        return None

    details['email'] = details['email'].lower().strip()
    try:
        user = User.objects.get(email__iexact=details['email'])
    except User.DoesNotExist:
        return None

    return {
        'user': user,
        'is_new': False,
    }


def create_or_update_user(backend: BaseAuth, details: dict[str, Any], user: User | None = None, **kwargs):
    if backend.name == 'password':
        return None

    if user is None:
        uuid = cast('str', details.get('uuid') or kwargs.get('uid'))
        user = User(uuid=uuid)
        msg = 'Created new user'
    else:
        msg = 'Existing user found'
        uuid = str(user.uuid)

    log_ctx = {
        'user.uuid': uuid,
        'user.email': details.get('email'),
    }
    logger.info(msg, **log_ctx)

    changed = False
    for field in ('first_name', 'last_name', 'email'):
        old_val = getattr(user, field)
        new_val = details.get(field)
        if field in ('first_name', 'last_name'):
            if old_val is None:
                old_val = ''
            if new_val is None:
                new_val = ''

        if new_val != old_val:
            setattr(user, field, new_val)
            changed = True

    if user.has_usable_password():
        user.set_unusable_password()
        changed = True

    if changed:
        logger.info('User saved', **log_ctx)
        user.save()

    return {
        'user': user,
    }


def update_avatar(backend: BaseAuth, details: dict[str, Any], user: User | None = None, **_kwargs):
    if backend.name != 'azure_ad' or user is None:
        return

    log_ctx = {
        'user.uuid': str(user.uuid),
        'user.email': details.get('email'),
    }
    log = logger.bind(**log_ctx)
    log.info('Updating user photo')

    person = user.get_corresponding_person()

    photo = None
    try:
        photo = get_user_photo_with_etag(user, old_etag=person.image_msgraph_etag if person else None)
    except Exception as e:
        log.exception('Failed to get user photo')
        capture_exception(e)

    if not photo:
        log.info('No photo found')
        return

    if photo.value is None:
        log.info('Photo unchanged; etag matched')
        return

    profile = UserProfile.get_for_user(user)

    photo_bytes = photo.value.content
    photo_hash = hashlib.md5(photo_bytes, usedforsecurity=False).hexdigest()
    if person:
        if person.image_hash == photo_hash:
            log.info('Photo unchanged; hashes match')
            person.image_msgraph_etag = photo.etag
            person.__class__.objects.filter(pk=person.pk).update(image_msgraph_etag=photo.etag)
            return
        try:
            person.set_avatar(photo_bytes, msgraph_etag=photo.etag)
        except Exception as e:
            log.exception('Failed to set avatar for person', **{'person.id': person.id})
            capture_exception(e)

    try:
        if not profile.avatar:
            profile.avatar.save('avatar.jpg', io.BytesIO(photo.value.content))
    except Exception as e:
        log.exception('Failed to set user profile photo')
        capture_exception(e)


def validate_user_password(strategy: BaseStrategy, backend: BaseAuth, user: User | None, **_kwargs):
    if backend.name != 'password':
        return

    password = strategy.request_data()['password']
    if user is None or not user.check_password(password) or not user.is_active:
        raise AuthForbidden(backend)
