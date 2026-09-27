"""Esquemas de entrada (Pydantic) y vistas de solo lectura de devoluciones (plan T5.2/T5.3)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from sistemashn.comercial.pagos.methods import PaymentInput
from sistemashn.core.money import money, qty


class ReturnCondition(StrEnum):
    """Estado físico de la pieza devuelta por un cliente."""

    VENDIBLE = "vendible"
    NO_VENDIBLE = "no_vendible"


class CustomerReturnResolution(StrEnum):
    """Cómo se resuelve una devolución de cliente."""

    REEMBOLSO = "reembolso"
    CAMBIO = "cambio"
    SALDO_A_FAVOR = "saldo_a_favor"


class SupplierReturnResolution(StrEnum):
    """Cómo responde el proveedor a una devolución."""

    REEMPLAZO = "reemplazo"
    REEMBOLSO = "reembolso"
    CREDITO_FUTURO = "credito_futuro"


class CustomerReturnInput(BaseModel):
    """Datos para registrar la devolución de una línea de venta."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sale_line_id: int | None = None
    product_id: int | None = None
    unit_price_override: Decimal | None = None
    qty: Decimal
    condition: ReturnCondition
    resolution: CustomerReturnResolution
    payment: PaymentInput | None = None
    reason: str | None = None
    request_id: str

    @field_validator("qty")
    @classmethod
    def _cantidad(cls, v: Decimal) -> Decimal:
        v = qty(v)
        if v <= 0:
            raise ValueError("la cantidad devuelta debe ser mayor a cero")
        return v

    @field_validator("unit_price_override")
    @classmethod
    def _precio_override(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        v = money(v)
        if v <= 0:
            raise ValueError("el precio de referencia de la devolución debe ser mayor a cero")
        return v

    @field_validator("reason")
    @classmethod
    def _motivo(cls, v: str | None) -> str | None:
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

    @model_validator(mode="after")
    def _pago_requerido(self) -> CustomerReturnInput:
        if self.resolution == CustomerReturnResolution.REEMBOLSO and self.payment is None:
            raise ValueError("la resolución 'reembolso' requiere un pago")
        return self

    @model_validator(mode="after")
    def _comprobante_o_referencia(self) -> CustomerReturnInput:
        if self.sale_line_id is None and (
            self.product_id is None or self.unit_price_override is None
        ):
            raise ValueError(
                "una devolución sin comprobante requiere 'product_id' y 'unit_price_override'"
            )
        return self


class SupplierReturnInput(BaseModel):
    """Datos para registrar la devolución de una línea de compra a su proveedor."""

    model_config = ConfigDict(str_strip_whitespace=True)

    purchase_line_id: int | None = None
    product_id: int | None = None
    unit_price_override: Decimal | None = None
    qty: Decimal
    resolution: SupplierReturnResolution
    reason: str | None = None
    request_id: str

    @field_validator("qty")
    @classmethod
    def _cantidad(cls, v: Decimal) -> Decimal:
        v = qty(v)
        if v <= 0:
            raise ValueError("la cantidad devuelta debe ser mayor a cero")
        return v

    @field_validator("unit_price_override")
    @classmethod
    def _precio_override(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        v = money(v)
        if v <= 0:
            raise ValueError("el precio de referencia de la devolución debe ser mayor a cero")
        return v

    @field_validator("reason")
    @classmethod
    def _motivo(cls, v: str | None) -> str | None:
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

    @model_validator(mode="after")
    def _comprobante_o_referencia(self) -> SupplierReturnInput:
        if self.purchase_line_id is None and (
            self.product_id is None or self.unit_price_override is None
        ):
            raise ValueError(
                "una devolución sin comprobante requiere 'product_id' y 'unit_price_override'"
            )
        return self


@dataclass(frozen=True)
class CustomerReturnView:
    """Detalle de una devolución de cliente ya registrada."""

    id: int
    sale_line_id: int | None
    product_id: int | None
    unit_price_override: Decimal | None
    qty: Decimal
    condition: str
    resolution: str
    amount: Decimal
    new_sale_id: int | None
    user_id: int
    reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class SupplierReturnView:
    """Detalle de una devolución a proveedor ya registrada."""

    id: int
    purchase_line_id: int | None
    product_id: int | None
    unit_price_override: Decimal | None
    qty: Decimal
    resolution: str
    amount: Decimal
    user_id: int
    reason: str | None
    created_at: datetime
