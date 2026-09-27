"""Vistas de solo lectura de caja (plan T4.3)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class CashSessionView:
    """Estado completo de una sesión de caja (abierta o cerrada)."""

    id: int
    opened_at: datetime
    closed_at: datetime | None
    opened_by: int
    closed_by: int | None
    opening_amount: Decimal
    expected_cash: Decimal | None
    counted_cash: Decimal | None
    difference: Decimal | None
    status: str
    notes: str | None


@dataclass(frozen=True)
class CashMovementView:
    """Un movimiento de caja (entrada/salida manual o cobro en efectivo)."""

    id: int
    occurred_at: datetime
    kind: str
    amount: Decimal
    reason: str | None
    ref_type: str | None
    ref_id: str | None
    user_id: int
