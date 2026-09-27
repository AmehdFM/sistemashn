"""Idempotencia de operaciones que crean documentos económicos (plan T3.1).

Toda operación que confirma un documento (compra, pago, etc.) recibe un `request_id` generado
por la UI. Si el mismo `request_id` se reenvía para la misma operación, el servicio debe
devolver el resultado anterior sin repetir la operación.
"""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, Session, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime
from sistemashn.core.errors import ValidationError


class IdempotencyRecord(Base):
    """Resultado recordado de una operación identificada por `request_id`."""

    __tablename__ = "com_idempotency"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    result_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


def find_previous(session: Session, request_id: str, operation: str) -> str | None:
    """Devuelve el `result_ref` recordado si `request_id` ya se procesó para `operation`.

    Si `request_id` se usó antes para una operación distinta, es un error de uso: el
    identificador no se puede reutilizar entre operaciones.
    """
    registro = session.get(IdempotencyRecord, request_id)
    if registro is None:
        return None
    if registro.operation != operation:
        raise ValidationError(
            f"request_id '{request_id}' ya se usó para la operación '{registro.operation}'"
        )
    return registro.result_ref


def remember(
    session: Session,
    request_id: str,
    operation: str,
    result_ref: str,
    clock: Callable[[], datetime],
) -> None:
    """Registra el resultado de `request_id` en la misma transacción del documento."""
    session.add(
        IdempotencyRecord(
            request_id=request_id,
            operation=operation,
            result_ref=result_ref,
            created_at=clock(),
        )
    )
    session.flush()
