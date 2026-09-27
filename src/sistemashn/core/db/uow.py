"""Unit of Work: ejecuta una función dentro de una transacción con reintentos (ADR-002)."""

import time
from collections.abc import Callable

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import DatabaseBusyError


def run_in_transaction[T](
    factory: sessionmaker[Session],
    fn: Callable[[Session], T],
    *,
    retries: int = 3,
    backoff: float = 0.05,
    readonly: bool = False,
) -> T:
    """Ejecuta `fn(session)` en `session_scope`, reintentando solo ante "database is locked"."""
    intento = 0
    while True:
        try:
            with session_scope(factory, readonly=readonly) as session:
                return fn(session)
        except OperationalError as exc:
            if "database is locked" not in str(exc):
                raise
            intento += 1
            if intento >= retries:
                raise DatabaseBusyError(
                    f"base de datos bloqueada tras {retries} reintentos"
                ) from exc
            time.sleep(backoff * intento)
