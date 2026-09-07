from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from kausal_common.storage import storage_settings_from_s3_url
from kausal_common.storage.storage_classes import MediaFilesS3Storage


def test_media_storage_does_not_overwrite_existing_files():
    """
    Uploads must not be allowed to land on a key that is already taken.

    With `file_overwrite` on, `get_available_name` returns the requested key even when another
    object uses it, so two objects end up sharing one file and deleting either destroys the other.
    """
    storage = MediaFilesS3Storage(bucket_name='test-bucket')

    assert storage.file_overwrite is False  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    ('value', 'expected'),
    [('false', False), ('False', False), ('no', False), ('off', False), ('true', True), ('yes', True)],
)
def test_boolean_options_are_parsed_from_the_query_string(value, expected):
    """Non-empty strings are truthy, so `?file_overwrite=false` must not switch overwriting on."""
    url = urlparse(f's3://key:secret@s3.example.com/bucket?file_overwrite={value}')

    settings = storage_settings_from_s3_url(url, deployment_type='production')

    assert settings['OPTIONS']['file_overwrite'] is expected


def test_non_boolean_options_are_left_as_strings():
    url = urlparse('s3://key:secret@s3.example.com/bucket?addressing_style=virtual')

    settings = storage_settings_from_s3_url(url, deployment_type='production')

    assert settings['OPTIONS']['addressing_style'] == 'virtual'
    assert settings['OPTIONS']['bucket_name'] == 'bucket'


def test_presigned_urls_are_signed_with_sigv4():
    """
    `Storage.url()` must hand out a SigV4 URL.

    Left to itself, botocore resolves the legacy S3 global endpoint, whose metadata lists SigV2
    ahead of SigV4, and signs presigned URLs with SigV2 — while signing every other call on the
    same client with SigV4. Ceph RGW rejects SigV2, so public media 403s while uploads succeed.
    """
    url = urlparse(
        's3://key:secret@fsn1.your-objectstorage.com/bucket?addressing_style=virtual',
    )

    settings = storage_settings_from_s3_url(url, deployment_type='production')
    storage = MediaFilesS3Storage(**settings['OPTIONS'])

    query = parse_qs(urlparse(storage.url('images/test.jpg')).query)
    assert query['X-Amz-Algorithm'] == ['AWS4-HMAC-SHA256']
    assert 'AWSAccessKeyId' not in query
    assert settings['OPTIONS']['signature_version'] == 's3v4'


def test_signature_version_can_be_overridden_from_the_query_string():
    url = urlparse('s3://key:secret@s3.example.com/bucket?signature_version=s3')

    settings = storage_settings_from_s3_url(url, deployment_type='production')

    assert settings['OPTIONS']['signature_version'] == 's3'
