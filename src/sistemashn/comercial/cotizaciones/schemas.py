"""Esquemas de entrada (Pydantic) y vistas de solo lectura de cotizaciones (plan T4.1)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from sistemashn.core.money import qty, rate


class QuoteLineInput(BaseModel):
    """Una línea capturada al crear una cotización."""

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


class QuoteInput(BaseModel):
    """Datos para crear una cotización, con o sin apartado de inventario."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: int | None = None
    lines: list[QuoteLineInput]
    valid_until: date
    reserve: bool = False
    notes: str | None = None
    request_id: str

    @field_validator("lines")
    @classmethod
    def _lineas(cls, v: list[QuoteLineInput]) -> list[QuoteLineInput]:
        if not v:
            raise ValueError("la cotización debe tener al menos una línea")
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
class QuoteLineView:
    """Línea de una cotización, tal como quedó persistida."""

    line_no: int
    product_id: int
    description_snapshot: str
    qty: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class QuoteView:
    """Detalle completo de una cotización."""

    id: int
    uuid: str
    number: str
    customer_id: int | None
    status: str
    valid_until: date
    has_reservation: bool
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime
    lines: tuple[QuoteLineView, ...]


@dataclass(frozen=True)
class QuoteSummary:
    """Fila resumida de una cotización, para listados."""

    id: int
    number: str
    customer_id: int | None
    status: str
    valid_until: date
    total: Decimal
    created_at: datetime
