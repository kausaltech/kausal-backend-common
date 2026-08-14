from __future__ import annotations

from urllib.parse import urlparse

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
