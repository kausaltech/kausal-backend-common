from __future__ import annotations

from urllib.parse import ParseResult, parse_qs


def storage_settings_from_s3_url(url: ParseResult, deployment_type: str | None = None):
    assert url.scheme == 's3'
    if deployment_type is None:
        from django.conf import settings
        deployment_type = settings.DEPLOYMENT_TYPE

    opts = {
        'bucket_name': url.path.lstrip('/'),
    }
    if url.hostname:
        opts['endpoint_url'] = f'https://{url.hostname}'
    if url.username:
        opts['access_key'] = url.username
    if url.password:
        opts['secret_key'] = url.password
    for key, val in parse_qs(url.query).items():
        assert len(val) == 1
        opts[key] = val[0]
    if deployment_type == 'production':
        backend = 'kausal_common.storage.storage_classes.MediaFilesS3Storage'
    else:
        backend = 'kausal_common.storage.storage_classes.LocalMediaStorageWithS3Fallback'
    return {
        'BACKEND': backend,
        'OPTIONS': opts,
    }
