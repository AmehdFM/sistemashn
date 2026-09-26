from __future__ import annotations

import time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from sistemashn.core.db.engine import create_engine_for_path
from sistemashn.core.db.models import Base, ProbeRecord
from sistemashn.core.db.session import session_scope


def test_engine_enables_foreign_keys_and_accepts_unicode_path(tmp_path) -> None:
    db_path = tmp_path / "Negocio José con espacios" / "datos.sqlite3"
    engine = create_engine_for_path(db_path)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert db_path.exists()
    finally:
        engine.dispose()


def test_session_commits_and_rolls_back_without_reusing_session(tmp_path) -> None:
    engine = create_engine_for_path(tmp_path / "datos.sqlite3")
    try:
        Base.metadata.create_all(engine)
        with session_scope(engine) as first:
            first.add(ProbeRecord(value="conservado"))
        with session_scope(engine) as second:
            assert first is not second
            assert [row.value for row in second.query(ProbeRecord).all()] == ["conservado"]
        with pytest.raises(ValueError, match="cancelar"):
            with session_scope(engine) as session:
                session.add(ProbeRecord(value="parcial"))
                session.flush()
                raise ValueError("cancelar")
        with session_scope(engine) as session:
            assert [row.value for row in session.query(ProbeRecord).all()] == ["conservado"]
    finally:
        engine.dispose()


def test_second_writer_times_out_without_corrupting_first(tmp_path) -> None:
    path = tmp_path / "bloqueada.sqlite3"
    first_engine = create_engine_for_path(path)
    second_engine = create_engine_for_path(path)
    try:
        with first_engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE probe_lock (id INTEGER PRIMARY KEY, value TEXT)")
        with first_engine.connect() as first:
            first.exec_driver_sql("INSERT INTO probe_lock (value) VALUES ('primero')")
            started = time.monotonic()
            with second_engine.connect() as second:
                with pytest.raises(OperationalError, match="locked"):
                    second.exec_driver_sql("INSERT INTO probe_lock (value) VALUES ('segundo')")
            assert time.monotonic() - started < 3.0
            first.commit()
        with first_engine.connect() as connection:
            values = connection.execute(text("SELECT value FROM probe_lock")).scalars().all()
            assert values == ["primero"]
    finally:
        first_engine.dispose()
        second_engine.dispose()
