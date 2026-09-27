"""Esquemas de entrada (Pydantic) y vistas de solo lectura de ventas (plan T4.2)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sistemashn.comercial.pagos.methods import PaymentInput
from sistemashn.core.money import qty, rate


class SaleLineInput(BaseModel):
    """Una línea capturada al confirmar una venta."""

    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int
    qty: Decimal
    unit_price: Decimal | None = None
    tax_rate: Decimal | None = None

    @field_validator("qty")
    @classmethod
    def _cantidad(cls, v: Decimal) -> Decimal:
        v = qty(v)
        if v <= 0:
            raise ValueError("la cantidad debe ser mayor a cero")
        return v

    @field_validator("unit_price")
    @classmethod
    def _precio(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        if v < 0:
            raise ValueError("el precio unitario no puede ser negativo")
        return v

    @field_validator("tax_rate")
    @classmethod
    def _tasa(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        return rate(v)


class SaleInput(BaseModel):
    """Datos para confirmar una venta, opcionalmente originada en una cotización."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: int | None = None
    quote_id: int | None = None
    lines: list[SaleLineInput]
    payments: list[PaymentInput] = Field(default_factory=list)
    credit_due_date: date | None = None
    cash_session_id: int | None = None
    accept_changes: bool = False
    notes: str | None = None
    request_id: str

    @field_validator("lines")
    @classmethod
    def _lineas(cls, v: list[SaleLineInput]) -> list[SaleLineInput]:
        if not v:
            raise ValueError("la venta debe tener al menos una línea")
        return v

    @field_validator("notes")
    @classmethod
    def _texto_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("request_id")
    @classmethod
    def _request_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("request_id no puede estar vacío")
        return v


@dataclass(frozen=True)
class SaleLineView:
    """Línea confirmada de una venta, tal como quedó persistida."""

    line_no: int
    product_id: int
    description_snapshot: str
    qty: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal
    unit_cost_snapshot: Decimal | None
    kit_component_of: int | None


@dataclass(frozen=True)
class SalePaymentView:
    """Pago aplicado a una venta."""

    method: str
    amount: Decimal
    reference: str | None


@dataclass(frozen=True)
class SaleView:
    """Detalle completo de una venta confirmada."""

    id: int
    uuid: str
    number: str
    quote_id: int | None
    customer_id: int | None
    sold_at: datetime
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    credit_amount: Decimal
    status: str
    cash_session_id: int | None
    notes: str | None
    created_at: datetime
    lines: tuple[SaleLineView, ...]
    payments: tuple[SalePaymentView, ...]


@dataclass(frozen=True)
class SaleSummary:
    """Fila resumida de una venta, para listados e historial por cliente."""

    id: int
    number: str
    customer_id: int | None
    sold_at: datetime
    total: Decimal
    status: str
