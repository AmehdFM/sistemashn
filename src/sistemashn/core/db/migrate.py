"""API programática de Alembic para aplicar/revertir migraciones sobre un archivo SQLite."""

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

# Las migraciones viajan dentro del paquete para que el build de Windows las incluya.
_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _alembic_config(db_path: Path) -> Config:
    cfg = Config()
    # `_MIGRATIONS_DIR` se lee en cada llamada: las pruebas lo sustituyen por migraciones de sonda.
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{Path(db_path)}")
    return cfg


def upgrade(db_path: Path, revision: str = "head") -> None:
    """Aplica migraciones hasta `revision` (por defecto la última)."""
    from alembic import command

    command.upgrade(_alembic_config(db_path), revision)


def downgrade(db_path: Path, revision: str) -> None:
    """Revierte migraciones hasta `revision`."""
    from alembic import command

    command.downgrade(_alembic_config(db_path), revision)


def current_revision(db_path: Path) -> str | None:
    """Revisión actual aplicada a la base, o None si no tiene ninguna."""
    engine = create_engine(f"sqlite+pysqlite:///{Path(db_path)}")
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    finally:
        engine.dispose()
