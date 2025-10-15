from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import requests
from loguru import logger

if TYPE_CHECKING:
    from users.models import User


logger = logger.bind(name='kausal_common.auth.msgraph')

def _get_token(user: User) -> str | None:
    auth = user.social_auth.filter(provider='azure_ad').first()
    if not auth:
        backends = [x.provider for x in user.social_auth.all()]
        logger.error('User logged in with %s, not with Azure AD' % ', '.join(backends))
        return None

    return auth.extra_data['access_token']


def graph_get(resource: str, token: str) -> requests.Response:
    headers = dict(authorization='Bearer %s' % token)
    return requests.get('https://graph.microsoft.com/v1.0/%s' % resource, headers=headers, timeout=5)


def graph_get_json(resource: str, token: str) -> dict[str, Any]:
    res = graph_get(resource, token)
    res.raise_for_status()
    return res.json()


def get_user_data(user: User, principal_name: str | None = None) -> dict[str, Any] | None:
    token = _get_token(user)
    if not token:
        return None
    if principal_name:
        resource = 'users/%s' % principal_name
    else:
        resource = 'me/'
    data = graph_get_json(resource, token)
    return data


@dataclass
class UserPhoto:
    value: requests.Response | None
    etag: str | None


def get_user_photo_with_etag(user: User, old_etag: str | None = None) -> UserPhoto | None:
    token = _get_token(user)
    if not token:
        return None

    data = graph_get_json('me/photo', token)
    etag = data.get('@odata.mediaEtag', None)
    logger.debug('New ETag: %s; old ETag: %s' % (etag, old_etag))
    if old_etag and old_etag == etag:
        return UserPhoto(value=None, etag=etag)

    out = graph_get('me/photo/$value', token)
    if out.status_code == 404:
        return None
    return UserPhoto(value=out, etag=etag)


def get_user_photo(user: User) -> requests.Response | None:
    photo = get_user_photo_with_etag(user)
    return photo.value if photo else None
