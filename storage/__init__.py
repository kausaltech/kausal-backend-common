from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

if TYPE_CHECKING:
    from urllib.parse import ParseResult

_BOOLEAN_OPTION_VALUES = {
    'true': True,
    'yes': True,
    'on': True,
    'false': False,
    'no': False,
    'off': False,
}


def _parse_option_value(value: str) -> str | bool:
    """
    Convert an option value that spells out a boolean.

    Everything in a query string arrives as a string, and a non-empty string is truthy: without
    this, `?file_overwrite=false` would switch overwriting on rather than off. Numeric values are
    left alone so that options which take a number aren't turned into booleans.
    """
    return _BOOLEAN_OPTION_VALUES.get(value.lower(), value)


def storage_settings_from_s3_url(url: ParseResult, deployment_type: str | None = None) -> dict[str, Any]:
    assert url.scheme == 's3'
    if deployment_type is None:
        from django.conf import settings

        deployment_type = settings.DEPLOYMENT_TYPE

    opts: dict[str, Any] = {
        'bucket_name': url.path.lstrip('/'),
        # Presigned URLs have to be signed with SigV4. django-storages leaves `signature_version`
        # unset, and botocore then resolves the legacy S3 global endpoint, whose metadata lists
        # `s3` (SigV2) ahead of `s3v4`; `generate_presigned_url` picks that first entry. The
        # result is that `Storage.url()` hands out a SigV2 URL (`AWSAccessKeyId`/`Signature`/
        # `Expires`) while every other call on the same client is signed with SigV4 — so uploads,
        # listings and copies all work and only public media 403s. Ceph RGW rejects SigV2, and
        # SigV4 is what boto3 already uses against these endpoints for everything else, so pin it.
        'signature_version': 's3v4',
    }
    if url.hostname:
        opts['endpoint_url'] = f'https://{url.hostname}'
    if url.username:
        opts['access_key'] = url.username
    if url.password:
        opts['secret_key'] = url.password
    # After the defaults above, so that the URL can still override them.
    for key, val in parse_qs(url.query).items():
        assert len(val) == 1
        opts[key] = _parse_option_value(val[0])
    if deployment_type in ('development', 'ci'):
        backend = 'kausal_common.storage.storage_classes.LocalMediaStorageWithS3Fallback'
    else:
        backend = 'kausal_common.storage.storage_classes.MediaFilesS3Storage'
    return {
        'BACKEND': backend,
        'OPTIONS': opts,
    }
