from django.db.backends.postgresql.base import (
    DatabaseWrapper as PostgresDatabaseWrapper
)
from django.db import close_old_connections, connection as db_connection
from psycopg.errors import InterfaceError


class DatabaseWrapper(PostgresDatabaseWrapper):
    def create_cursor(self, name=None):
        try:
            return super().create_cursor(name=name)
        except InterfaceError:
            close_old_connections()
            db_connection.connect()
            return super().create_cursor(name=name)
