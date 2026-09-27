"""Esquemas y vistas de solo lectura de cuentas por pagar/cobrar (plan T3.3)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class AccountKind(StrEnum):
    """Naturaleza de la cuenta: por pagar (a un proveedor) o por cobrar (a un cliente)."""

    PAYABLE = "payable"
    RECEIVABLE = "receivable"
    CREDIT_NOTE = "credit_note"


class AccountStatus(StrEnum):
    """Estado derivado de una cuenta: nunca se guarda, se calcula al consultar."""

    PENDIENTE = "pendiente"
    VENCIDA = "vencida"
    PAGADA = "pagada"


@dataclass(frozen=True)
class AccountPaymentView:
    """Un abono aplicado a una cuenta."""

    id: int
    paid_at: datetime
    method: str
    amount: Decimal
    reference: str | None
    user_id: int


@dataclass(frozen=True)
class AccountSummary:
    """Fila resumida de una cuenta, para listados."""

    id: int
    kind: AccountKind
    party_id: int
    party_name: str
    source_type: str
    source_id: str
    original_amount: Decimal
    balance: Decimal
    due_date: date
    status: AccountStatus
    days_overdue: int


@dataclass(frozen=True)
class AccountView(AccountSummary):
    """Detalle completo de una cuenta, con su historial de abonos."""

    created_at: datetime = datetime(1970, 1, 1)
    payments: tuple[AccountPaymentView, ...] = ()
