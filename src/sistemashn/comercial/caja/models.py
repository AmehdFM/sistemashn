"""Modelos de caja: sesiones de turno y movimientos append-only (plan T4.3)."""

from datetime import datetime

from sqlalchemy import (
    DDL,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money, UtcDateTime

_RAISE_APPEND_ONLY = "RAISE(ABORT, 'cash movement is append-only')"

# Igual patrón que `comercial.credito.models`: la migración de la fase reutiliza estas sentencias.
CASH_MOVEMENT_TRIGGERS_SQL: tuple[str, ...] = (
    f"""
    CREATE TRIGGER trg_com_cash_movement_no_update
    BEFORE UPDATE ON com_cash_movement
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
    f"""
    CREATE TRIGGER trg_com_cash_movement_no_delete
    BEFORE DELETE ON com_cash_movement
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
)


class CashSession(Base):
    """Una apertura/cierre de caja (un usuario, un período)."""

    __tablename__ = "com_cash_session"
    __table_args__ = (
        CheckConstraint("status IN ('abierta', 'cerrada')", name="status_valido"),
        CheckConstraint("opening_amount >= 0", name="opening_amount_no_negativo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opened_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    opened_by: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opening_amount: Mapped[object] = mapped_column(Money(), nullable=False)
    expected_cash: Mapped[object | None] = mapped_column(Money(), nullable=True)
    counted_cash: Mapped[object | None] = mapped_column(Money(), nullable=True)
    difference: Mapped[object | None] = mapped_column(Money(), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)


class CashMovement(Base):
    """Movimiento de caja inmutable: entrada/salida manual o cobro en efectivo."""

    __tablename__ = "com_cash_movement"
    __table_args__ = (
        CheckConstraint("kind IN ('entrada', 'salida', 'venta', 'abono')", name="kind_valido"),
        CheckConstraint("amount > 0", name="amount_positivo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cash_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("com_cash_session.id"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[object] = mapped_column(Money(), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    ref_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)


for _sql in CASH_MOVEMENT_TRIGGERS_SQL:
    event.listen(
        CashMovement.__table__,
        "after_create",
        DDL(_sql).execute_if(dialect="sqlite"),
    )
