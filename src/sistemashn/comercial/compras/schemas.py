"""Esquemas de entrada (Pydantic) y vistas de solo lectura de compras (plan T3.2)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sistemashn.comercial.pagos.methods import PaymentInput
from sistemashn.comercial.presentacion import PresentationSnapshot, validate_presentation_quantity
from sistemashn.core.money import qty, rate, unit_cost


class PurchaseLineInput(BaseModel):
    """Una línea capturada al confirmar una compra."""

    model_config = ConfigDict(str_strip_whitespace=True)

    product_id: int
    qty: Decimal
    unit_cost: Decimal
    tax_rate: Decimal | None = None
    presentation: PresentationSnapshot | None = None

    @model_validator(mode="after")
    def _presentacion(self) -> PurchaseLineInput:
        validate_presentation_quantity(self.qty, self.presentation)
        if self.presentation is not None:
            amount = self.presentation.unit_amount
            if amount is None or amount != self.unit_cost * self.presentation.factor_base:
                raise ValueError("costo de presentación no coincide con el costo base")
        return self

    @field_validator("qty")
    @classmethod
    def _cantidad(cls, v: Decimal) -> Decimal:
        v = qty(v)
        if v <= 0:
            raise ValueError("la cantidad debe ser mayor a cero")
        return v

    @field_validator("unit_cost")
    @classmethod
    def _costo(cls, v: Decimal) -> Decimal:
        v = unit_cost(v)
        if v < 0:
            raise ValueError("el costo unitario no puede ser negativo")
        return v

    @field_validator("tax_rate")
    @classmethod
    def _tasa(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        return rate(v)


class PurchaseInput(BaseModel):
    """Datos para confirmar una compra a un proveedor."""

    model_config = ConfigDict(str_strip_whitespace=True)

    supplier_id: int
    supplier_invoice_ref: str | None = None
    lines: list[PurchaseLineInput]
    payments: list[PaymentInput] = Field(default_factory=list)
    credit_due_date: date | None = None
    notes: str | None = None
    request_id: str

    @field_validator("lines")
    @classmethod
    def _lineas(cls, v: list[PurchaseLineInput]) -> list[PurchaseLineInput]:
        if not v:
            raise ValueError("la compra debe tener al menos una línea")
        return v

    @field_validator("supplier_invoice_ref", "notes")
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
class PurchaseLineView:
    """Línea confirmada de una compra, tal como quedó persistida."""

    line_no: int
    product_id: int
    description_snapshot: str
    qty: Decimal
    unit_cost: Decimal | None
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal
    presentation: PresentationSnapshot | None = None


@dataclass(frozen=True)
class PurchasePaymentView:
    """Pago aplicado a una compra."""

    method: str
    amount: Decimal
    reference: str | None


@dataclass(frozen=True)
class PurchaseView:
    """Detalle completo de una compra confirmada."""

    id: int
    uuid: str
    number: str
    supplier_id: int
    supplier_invoice_ref: str | None
    purchased_at: datetime
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    paid_initial: Decimal
    credit_amount: Decimal
    status: str
    notes: str | None
    created_at: datetime
    lines: tuple[PurchaseLineView, ...]
    payments: tuple[PurchasePaymentView, ...]


@dataclass(frozen=True)
class PurchaseSummary:
    """Fila resumida de una compra, para listados e historial por proveedor."""

    id: int
    number: str
    supplier_id: int
    supplier_name: str
    purchased_at: datetime
    total: Decimal
    status: str


@dataclass(frozen=True)
class SupplierPriceView:
    """Un costo histórico de un producto con un proveedor."""

    product_id: int
    unit_cost: Decimal
    purchase_id: int
    recorded_at: datetime
