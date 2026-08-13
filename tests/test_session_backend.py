from django.contrib.auth import BACKEND_SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore

import pytest
from asgiref.sync import async_to_sync

from kausal_common.sessions.backends.db import AZURE_AD_BACKEND_PATH, SessionStore

pytestmark = pytest.mark.django_db


def create_legacy_session(backend_path: str) -> str:
    session = DatabaseSessionStore()
    session[BACKEND_SESSION_KEY] = backend_path
    session.create()
    assert session.session_key is not None
    return session.session_key


@pytest.mark.parametrize(
    'legacy_path',
    [
        'admin_site.backends.AzureADAuth',
        'admin_site.auth_backends.AzureADAuth',
    ],
)
def test_load_migrates_legacy_azure_ad_backend_path(legacy_path: str):
    session_key = create_legacy_session(legacy_path)
    session = SessionStore(session_key)

    assert session[BACKEND_SESSION_KEY] == AZURE_AD_BACKEND_PATH
    assert session.modified is True

    session.save()
    assert DatabaseSessionStore(session_key)[BACKEND_SESSION_KEY] == AZURE_AD_BACKEND_PATH


def test_aload_migrates_legacy_azure_ad_backend_path():
    session_key = create_legacy_session('admin_site.backends.AzureADAuth')
    session = SessionStore(session_key)

    session_data = async_to_sync(session.aload)()

    assert session_data[BACKEND_SESSION_KEY] == AZURE_AD_BACKEND_PATH
    assert session.modified is True


def test_load_does_not_modify_current_backend_path():
    session_key = create_legacy_session(AZURE_AD_BACKEND_PATH)
    session = SessionStore(session_key)

    assert session[BACKEND_SESSION_KEY] == AZURE_AD_BACKEND_PATH
    assert session.modified is False
