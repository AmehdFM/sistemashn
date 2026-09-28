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


class NoMigrationsFoundError(RuntimeError):
    """`_MIGRATIONS_DIR` no tiene ninguna migración: `upgrade()` sería un no-op silencioso.

    Pasa desapercibido con facilidad: Alembic no lanza error al "migrar" una cadena vacía,
    así que sin este chequeo la base queda sin tablas y el primer síntoma real aparece varios
    pasos después, como un "no such table" confuso al primer arranque (visto en builds
    empaquetados de Windows donde `migrations/versions/*.py` no llegó a incluirse en el
    ejecutable).
    """


def upgrade(db_path: Path, revision: str = "head") -> None:
    """Aplica migraciones hasta `revision` (por defecto la última)."""
    from alembic import command
    from alembic.script import ScriptDirectory

    cfg = _alembic_config(db_path)
    if not ScriptDirectory.from_config(cfg).get_heads():
        raise NoMigrationsFoundError(
            f"No se encontró ninguna migración en '{_MIGRATIONS_DIR}'. Revise que "
            "'migrations/versions/*.py' se haya incluido en el paquete/instalación."
        )
    command.upgrade(cfg, revision)


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
