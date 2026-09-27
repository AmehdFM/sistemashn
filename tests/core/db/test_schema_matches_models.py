"""El esquema producido por la cadena real de migraciones debe coincidir con los modelos."""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from sistemashn.core.db.base import Base
from sistemashn.core.db.migrate import upgrade
from sistemashn.core.db.model_registry import import_all_models

TRIGGERS_ESPERADOS = (
    "trg_core_audit_event_no_update",
    "trg_core_audit_event_no_delete",
    "trg_com_account_payment_no_update",
    "trg_com_account_payment_no_delete",
    "trg_com_stock_movement_no_update",
    "trg_com_stock_movement_no_delete",
)


def _migrated_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "schema.db"
    upgrade(db_path)
    return db_path


def test_migracion_0001_reproduce_exactamente_los_modelos(tmp_path: Path) -> None:
    import_all_models()
    db_path = _migrated_db(tmp_path)

    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            contexto = MigrationContext.configure(connection, opts={"compare_type": True})
            diferencias = compare_metadata(contexto, Base.metadata)
    finally:
        engine.dispose()

    assert diferencias == []


def test_migracion_0001_crea_los_triggers_append_only(tmp_path: Path) -> None:
    db_path = _migrated_db(tmp_path)

    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.connect() as connection:
            nombres = {
                fila[0]
                for fila in connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
                )
            }
    finally:
        engine.dispose()

    for nombre in TRIGGERS_ESPERADOS:
        assert nombre in nombres
