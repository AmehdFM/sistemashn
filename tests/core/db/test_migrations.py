"""Pruebas de sistemashn.core.db.migrate contra un archivo SQLite real."""

import pytest
from sqlalchemy import create_engine, text

from sistemashn.core.db.migrate import current_revision, downgrade, upgrade

pytestmark = pytest.mark.usefixtures("probe_migrations")


def test_upgrade_0001_inserta_fila(tmp_path) -> None:
    db_path = tmp_path / "m1.db"
    upgrade(db_path, "0001")
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO probe_records (id, value) VALUES (1, 'a')"))
        assert current_revision(db_path) == "0001"
    finally:
        engine.dispose()


def test_upgrade_0002_conserva_datos_y_agrega_note(tmp_path) -> None:
    db_path = tmp_path / "m2.db"
    upgrade(db_path, "0001")
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO probe_records (id, value) VALUES (1, 'a')"))
    finally:
        engine.dispose()

    upgrade(db_path, "0002")

    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT id, value, note FROM probe_records WHERE id = 1")).one()
        assert row.id == 1
        assert row.value == "a"
        assert row.note == ""
        assert current_revision(db_path) == "0002"
    finally:
        engine.dispose()


def test_downgrade_a_0001_conserva_id_value(tmp_path) -> None:
    db_path = tmp_path / "m3.db"
    upgrade(db_path, "head")
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO probe_records (id, value, note) VALUES (1, 'a', 'n')"))
    finally:
        engine.dispose()

    downgrade(db_path, "0001")

    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT id, value FROM probe_records WHERE id = 1")).one()
            cols = {c[1] for c in conn.execute(text("PRAGMA table_info(probe_records)"))}
        assert row.id == 1
        assert row.value == "a"
        assert "note" not in cols
        assert current_revision(db_path) == "0001"
    finally:
        engine.dispose()


def test_upgrade_head_conserva_datos_tras_ida_y_vuelta(tmp_path) -> None:
    db_path = tmp_path / "m4.db"
    upgrade(db_path, "head")
    downgrade(db_path, "0001")
    upgrade(db_path, "head")
    assert current_revision(db_path) == "0002"


def test_current_revision_none_sin_migrar(tmp_path) -> None:
    db_path = tmp_path / "m5.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    engine.dispose()
    assert current_revision(db_path) is None
