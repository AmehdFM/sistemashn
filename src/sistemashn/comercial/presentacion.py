"""Snapshot inmutable de una presentación usada en una línea comercial."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PresentationSnapshot(BaseModel):
    """Datos originales de empaque/medida; `qty` de la línea sigue en unidad base."""

    model_config = ConfigDict(str_strip_whitespace=True)

    pack_id: int = Field(gt=0)
    label: str = Field(min_length=1, max_length=100)
    factor_base: Decimal
    quantity: Decimal
    unit_amount: Decimal | None = None

    @model_validator(mode="after")
    def valid_numbers(self) -> PresentationSnapshot:
        if not self.factor_base.is_finite() or self.factor_base <= 0:
            raise ValueError("factor de presentación inválido")
        if not self.quantity.is_finite() or self.quantity <= 0:
            raise ValueError("cantidad de presentación inválida")
        if self.unit_amount is not None and (
            not self.unit_amount.is_finite() or self.unit_amount < 0
        ):
            raise ValueError("importe de presentación inválido")
        return self


def validate_presentation_quantity(
    base_quantity: Decimal, snapshot: PresentationSnapshot | None
) -> None:
    if snapshot is not None and snapshot.factor_base * snapshot.quantity != base_quantity:
        raise ValueError("la presentación no coincide con la cantidad en unidad base")
