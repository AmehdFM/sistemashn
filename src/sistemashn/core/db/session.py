"""Fábrica de sesiones y scope transaccional (ADR-002: una sesión por tarea/hilo)."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.db.engine import READONLY_OPTION


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Sessionmaker con `expire_on_commit=False` (los objetos siguen usables tras commit)."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session], *, readonly: bool = False) -> Iterator[Session]:
    """Abre una sesión, hace commit al salir sin error, rollback y re-lanza si hay error.

    Por defecto la transacción es de escritura (BEGIN IMMEDIATE). Con `readonly=True` usa
    BEGIN diferido y no toma el candado de escritura (consultas, reportes, respaldos).
    """
    session = factory()
    if readonly:
        session.connection(execution_options={READONLY_OPTION: True})
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
