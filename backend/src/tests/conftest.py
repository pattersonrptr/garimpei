"""Settings shared by every test."""

import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite ignores foreign keys unless asked; Postgres always enforces them.

    Turning them on makes the test databases behave like production for
    referential integrity (``ON DELETE`` rules included).
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
