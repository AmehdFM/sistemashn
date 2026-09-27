"""Método de pago y captura de un pago individual (plan T3.1)."""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

from sistemashn.core.money import money


class PaymentMethod(StrEnum):
    """Métodos de pago aceptados en compras y ventas."""

    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"


class PaymentInput(BaseModel):
    """Un pago (efectivo, tarjeta o transferencia) aplicado a un documento."""

    model_config = ConfigDict(str_strip_whitespace=True)

    method: PaymentMethod
    amount: Decimal
    reference: str | None = None

    @field_validator("amount")
    @classmethod
    def _monto(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("el monto del pago debe ser mayor a cero")
        return money(v)

    @field_validator("reference")
    @classmethod
    def _referencia(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 60:
            raise ValueError("la referencia de pago no puede exceder 60 caracteres")
        return v
