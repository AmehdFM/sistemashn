"""Motor SQLite del proyecto: PRAGMAs por conexión y ubicación de datos (ADR-002)."""

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event

READONLY_OPTION = "sistemashn_readonly"


def data_dir(vertical: str = "repuestos") -> Path:
    """Carpeta de datos del vertical. `SISTEMASHN_DATA_DIR` tiene prioridad total."""
    override = os.environ.get("SISTEMASHN_DATA_DIR")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA")
    raiz = Path(base) if base else Path.home() / "AppData" / "Local"
    return raiz / "SistemasHN" / vertical


def create_engine_for_path(path: Path, *, busy_timeout_ms: int = 5000) -> Engine:
    """Crea el Engine SQLite en `path`, asegurando la carpeta padre y los PRAGMAs de ADR-002."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite+pysqlite:///{path}", future=True)

    @event.listens_for(engine, "connect")
    def _aplicar_pragmas(dbapi_connection, connection_record) -> None:
        # Desactiva el BEGIN implícito de pysqlite; lo emite el listener "begin".
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=FULL")
            cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        finally:
            cursor.close()

    @event.listens_for(engine, "begin")
    def _begin(conn) -> None:
        # Escrituras: BEGIN IMMEDIATE toma el candado al inicio, así "database is locked"
        # solo ocurre antes de hacer trabajo y el reintento es seguro. Lecturas: BEGIN diferido
        # para no bloquear a los escritores (WAL).
        if conn.get_execution_options().get(READONLY_OPTION):
            conn.exec_driver_sql("BEGIN")
        else:
            conn.exec_driver_sql("BEGIN IMMEDIATE")

    return engine
