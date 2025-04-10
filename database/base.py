from __future__ import annotations

from typing import Any

from django.contrib.gis.db.backends.postgis.base import (
    DatabaseWrapper as PostgisDatabaseWrapper,
)
from django.db import close_old_connections, connection as db_connection
from django.db.utils import DEFAULT_DB_ALIAS

from psycopg.errors import InterfaceError, OperationalError


class DatabaseWrapper(PostgisDatabaseWrapper):
    def __init__(self, settings_dict: dict[str, Any], alias: str = DEFAULT_DB_ALIAS):
        opts = settings_dict.setdefault('OPTIONS', {})
        opts.setdefault('pool', True)
        settings_dict.setdefault('CONN_HEALTH_CHECKS', True)
        super().__init__(settings_dict, alias=alias)

    def create_cursor(self, name=None):
        # Try to create a cursor, and if it fails, close the old connections and try again
        # one more time.
        try:
            return super().create_cursor(name=name)
        except (InterfaceError, OperationalError):
            close_old_connections()
            db_connection.connect()
            return super().create_cursor(name=name)
