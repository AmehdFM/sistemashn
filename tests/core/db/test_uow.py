"""Pruebas de session_scope y run_in_transaction (ADR-002)."""

import sqlite3

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from tests.fixtures.probe_models import ProbeBase as Base
from tests.fixtures.probe_models import ProbeRecord

from sistemashn.core.db.engine import create_engine_for_path
from sistemashn.core.db.session import make_session_factory, session_scope
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import DatabaseBusyError


@pytest.fixture
def engine(tmp_path):
    eng = create_engine_for_path(tmp_path / "uow.db")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def factory(engine):
    return make_session_factory(engine)


def test_session_scope_confirma_al_salir(factory) -> None:
    with session_scope(factory) as session:
        session.add(ProbeRecord(value="ok"))
    with session_scope(factory) as session:
        assert session.scalar(select(ProbeRecord)).value == "ok"


def test_session_scope_revierte_ante_error(factory) -> None:
    with pytest.raises(ValueError), session_scope(factory) as session:
        session.add(ProbeRecord(value="no-debe-quedar"))
        session.flush()
        raise ValueError("boom")
    with session_scope(factory) as session:
        assert session.scalar(select(ProbeRecord)) is None


def test_run_in_transaction_no_reintenta_otros_errores(factory) -> None:
    llamadas = {"n": 0}

    def fn(session):
        llamadas["n"] += 1
        raise ValueError("no es un bloqueo")

    with pytest.raises(ValueError):
        run_in_transaction(factory, fn, retries=3, backoff=0)
    assert llamadas["n"] == 1


def test_run_in_transaction_agota_reintentos_por_bloqueo(tmp_path) -> None:
    ruta = tmp_path / "bloqueo.db"
    eng = create_engine_for_path(ruta, busy_timeout_ms=50)
    Base.metadata.create_all(eng)
    factory = make_session_factory(eng)

    bloqueador = sqlite3.connect(str(ruta), timeout=0)
    bloqueador.execute("BEGIN IMMEDIATE")
    bloqueador.execute("INSERT INTO probe_records (value, note) VALUES ('x', '')")

    def fn(session):
        session.add(ProbeRecord(value="deberia-fallar"))

    try:
        with pytest.raises(DatabaseBusyError):
            run_in_transaction(factory, fn, retries=2, backoff=0.01)
    finally:
        bloqueador.rollback()
        bloqueador.close()
        eng.dispose()


def test_operational_error_no_lock_no_se_reintenta(factory) -> None:
    llamadas = {"n": 0}

    def fn(session):
        llamadas["n"] += 1
        raise OperationalError("stmt", {}, Exception("otra falla"))

    with pytest.raises(OperationalError):
        run_in_transaction(factory, fn, retries=3, backoff=0)
    assert llamadas["n"] == 1


def test_escritura_toma_candado_al_inicio_y_lectura_no(tmp_path) -> None:
    """BEGIN IMMEDIATE en escrituras; una lectura concurrente no queda bloqueada."""
    engine = create_engine_for_path(tmp_path / "lock.db", busy_timeout_ms=50)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        session.add(ProbeRecord(value="a"))

    with session_scope(factory) as writer:
        writer.connection()  # abre la transacción de escritura sin escribir todavía
        other = sqlite3.connect(tmp_path / "lock.db", timeout=0.05)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute("BEGIN IMMEDIATE")
        finally:
            other.close()
        with session_scope(factory, readonly=True) as reader:
            assert reader.query(ProbeRecord).count() == 1
    engine.dispose()
