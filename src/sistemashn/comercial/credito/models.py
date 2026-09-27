"""Modelos de cuentas por pagar/cobrar (`com_account`, `com_account_payment`, plan T3.3).

Diseño común: en la Fase 3 solo se usan cuentas `payable` (compras a crédito); la Fase 4
reutiliza exactamente el mismo esquema para cuentas `receivable` (ventas a crédito).
"""

from datetime import date, datetime

from sqlalchemy import (
    DDL,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money, UtcDateTime

_RAISE_APPEND_ONLY = "RAISE(ABORT, 'account payment is append-only')"

# Igual patrón que `core.audit.models`: la migración de la fase reutiliza estas sentencias.
ACCOUNT_PAYMENT_TRIGGERS_SQL: tuple[str, ...] = (
    f"""
    CREATE TRIGGER trg_com_account_payment_no_update
    BEFORE UPDATE ON com_account_payment
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
    f"""
    CREATE TRIGGER trg_com_account_payment_no_delete
    BEFORE DELETE ON com_account_payment
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
)


class Account(Base):
    """Cuenta por pagar (a un proveedor) o por cobrar (a un cliente)."""

    __tablename__ = "com_account"
    __table_args__ = (
        CheckConstraint("kind IN ('payable', 'receivable')", name="kind_valido"),
        CheckConstraint("original_amount > 0", name="original_amount_positivo"),
        CheckConstraint("balance >= 0", name="balance_no_negativo"),
        CheckConstraint("balance <= original_amount", name="balance_no_mayor_original"),
        UniqueConstraint("kind", "source_type", "source_id", name="uq_com_account_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    party_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_party.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str] = mapped_column(String(40), nullable=False)
    original_amount: Mapped[object] = mapped_column(Money(), nullable=False)
    balance: Mapped[object] = mapped_column(Money(), nullable=False)
    due_date: Mapped[date] = mapped_column(Date(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)


class AccountPayment(Base):
    """Abono inmutable aplicado a una cuenta (una fila por pago)."""

    __tablename__ = "com_account_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_account.id"), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[object] = mapped_column(Money(), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(60), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    __table_args__ = (CheckConstraint("amount > 0", name="amount_positivo"),)


for _sql in ACCOUNT_PAYMENT_TRIGGERS_SQL:
    event.listen(
        AccountPayment.__table__,
        "after_create",
        DDL(_sql).execute_if(dialect="sqlite"),
    )
