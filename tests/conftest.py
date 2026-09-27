"""Fixtures comunes: base SQLite temporal con el esquema de los modelos y reloj fijo."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.db.base import Base
from sistemashn.core.db.engine import create_engine_for_path
from sistemashn.core.db.session import make_session_factory

FIXED_NOW = datetime(2026, 9, 26, 15, 0, tzinfo=UTC)


def _import_all_models() -> None:
    """Registra en Base.metadata todos los modelos existentes (los agregan las fases)."""
    from sistemashn.core.db.model_registry import import_all_models

    import_all_models()


@pytest.fixture
def db_engine(tmp_path) -> Iterator[Engine]:
    _import_all_models()
    engine = create_engine_for_path(tmp_path / "test.db")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine) -> sessionmaker[Session]:
    return make_session_factory(db_engine)


@pytest.fixture
def now() -> datetime:
    return FIXED_NOW


@pytest.fixture
def clock(now):
    return lambda: now


@pytest.fixture(autouse=True)
def _argon2_rapido(monkeypatch) -> None:
    """Argon2 con parámetros mínimos solo en pruebas (la app usa los valores por defecto)."""
    from argon2 import PasswordHasher

    from sistemashn.core.identity import passwords, recovery

    rapido = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    monkeypatch.setattr(passwords, "_hasher", rapido)
    monkeypatch.setattr(recovery, "_code_hasher", rapido)


@pytest.fixture
def probe_migrations(monkeypatch) -> None:
    """Sustituye las migraciones del producto por la cadena de sonda 0001→0002 (pruebas de
    pipeline de migración, respaldo y actualización)."""
    from pathlib import Path

    from sistemashn.core.db import migrate

    monkeypatch.setattr(
        migrate, "_MIGRATIONS_DIR", Path(__file__).parent / "fixtures" / "probe_migrations"
    )
