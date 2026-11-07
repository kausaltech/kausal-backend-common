from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from django.contrib.staticfiles import finders

import pytest

from kausal_common.storage import storage_settings_from_s3_url
from kausal_common.storage.static import CheckedStaticFilesStorage
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


EXISTING_STATIC_FILE = 'wagtailadmin/css/core.css'


def test_checked_static_storage_gives_unhashed_url():
    storage = CheckedStaticFilesStorage()

    assert storage.url(EXISTING_STATIC_FILE) == f'{storage.base_url}{EXISTING_STATIC_FILE}'


@pytest.mark.parametrize('name', ['wagtailadmin/css/does-not-exist.css', 'wagtailadmin/css/does-not-exist.woff?#iefix'])
def test_checked_static_storage_rejects_missing_file(name):
    """A mistyped `{% static %}` path must fail, as it does with the manifest storage."""
    storage = CheckedStaticFilesStorage()

    with pytest.raises(ValueError, match='does-not-exist'):
        storage.url(name)


@pytest.mark.parametrize(
    ('name', 'expected_suffix'),
    [
        (f'{EXISTING_STATIC_FILE}#fragment', f'{EXISTING_STATIC_FILE}#fragment'),
        (f'{EXISTING_STATIC_FILE}?v=1', f'{EXISTING_STATIC_FILE}?v=1'),
        (f'{EXISTING_STATIC_FILE}?#iefix', f'{EXISTING_STATIC_FILE}?#iefix'),
        ('wagtailadmin/css/%63ore.css', EXISTING_STATIC_FILE),
        ('wagtailadmin/css/', 'wagtailadmin/css/'),
    ],
)
def test_checked_static_storage_builds_urls_like_the_manifest_storage(name, expected_suffix):
    """Apart from the hash, the URL must be what the manifest storage builds for the same name."""
    storage = CheckedStaticFilesStorage()

    assert storage.url(name) == f'{storage.base_url}{expected_suffix}'


def test_checked_static_storage_rejects_directory_without_trailing_slash():
    """The manifest storage has no entry for a directory, so it fails on one."""
    with pytest.raises(ValueError, match='wagtailadmin/css'):
        CheckedStaticFilesStorage().url('wagtailadmin/css')


@pytest.mark.parametrize(
    'name',
    [
        'wagtailadmin/css/../css/core.css',
        './wagtailadmin/css/core.css',
        'wagtailadmin//css/core.css',
        '../core.css',
        '..',
        '.',
    ],
)
def test_checked_static_storage_rejects_noncanonical_path(name):
    """The finders normalize these to an existing file, but the manifest storage has no entry for them."""
    with pytest.raises(ValueError, match='Static file not found'):
        CheckedStaticFilesStorage().url(name)


def test_checked_static_storage_rejects_absolute_path():
    """An absolute path inside a static directory is found by the finders, but it isn't a static file name."""
    absolute_path = finders.find(EXISTING_STATIC_FILE)
    assert isinstance(absolute_path, str)

    with pytest.raises(ValueError, match='Static file not found'):
        CheckedStaticFilesStorage().url(absolute_path)


def test_checked_static_storage_notices_when_the_finders_change(settings, tmp_path):
    """
    A test may override the settings the finders depend on, and Django keeps the storage then.

    The storage must not answer from what it found under the previous settings.
    """
    storage = CheckedStaticFilesStorage()
    (tmp_path / 'added-by-test.css').touch()

    with pytest.raises(ValueError, match='added-by-test'):
        storage.url('added-by-test.css')

    settings.STATICFILES_DIRS = [*settings.STATICFILES_DIRS, str(tmp_path)]
    assert storage.url('added-by-test.css') == f'{storage.base_url}added-by-test.css'

    settings.STATICFILES_DIRS = [d for d in settings.STATICFILES_DIRS if d != str(tmp_path)]
    with pytest.raises(ValueError, match='added-by-test'):
        storage.url('added-by-test.css')


def test_checked_static_storage_notices_files_created_on_disk(settings, tmp_path):
    settings.STATICFILES_DIRS = [*settings.STATICFILES_DIRS, str(tmp_path)]
    storage = CheckedStaticFilesStorage()

    with pytest.raises(ValueError, match='created-by-test'):
        storage.url('created-by-test.css')

    (tmp_path / 'created-by-test.css').touch()
    assert storage.url('created-by-test.css') == f'{storage.base_url}created-by-test.css'
