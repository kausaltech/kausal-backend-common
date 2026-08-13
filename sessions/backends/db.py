from __future__ import annotations

from typing import Any

from django.contrib.auth import BACKEND_SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore

AZURE_AD_BACKEND_PATH = 'kausal_common.auth.backends.AzureADAuth'
AUTH_BACKEND_PATH_MIGRATIONS = {
    'admin_site.backends.AzureADAuth': AZURE_AD_BACKEND_PATH,
    'admin_site.auth_backends.AzureADAuth': AZURE_AD_BACKEND_PATH,
}


class SessionStore(DatabaseSessionStore):
    """Database session store that migrates renamed authentication backends."""

    def _migrate_auth_backend_path(self, session_data: dict[str, Any]) -> dict[str, Any]:
        old_path = session_data.get(BACKEND_SESSION_KEY)
        if not isinstance(old_path, str):
            return session_data
        new_path = AUTH_BACKEND_PATH_MIGRATIONS.get(old_path)
        if new_path is None:
            return session_data

        session_data[BACKEND_SESSION_KEY] = new_path
        self.modified = True
        return session_data

    def load(self) -> dict[str, Any]:
        return self._migrate_auth_backend_path(super().load())

    async def aload(self) -> dict[str, Any]:
        return self._migrate_auth_backend_path(await super().aload())
