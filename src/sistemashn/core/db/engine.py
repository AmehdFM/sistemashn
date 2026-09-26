"""Configuración SQLite que aplica a cada conexión."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL


SQLITE_BUSY_TIMEOUT_MS = 500


def create_engine_for_path(path: Path) -> Engine:
    database_path = path.expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"autocommit": False, "timeout": SQLITE_BUSY_TIMEOUT_MS / 1000},
    )

    @event.listens_for(engine, "connect")
    def configure_connection(dbapi_connection, _connection_record) -> None:
        previous_autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        try:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=FULL")
            finally:
                cursor.close()
        finally:
            dbapi_connection.autocommit = previous_autocommit

    return engine
