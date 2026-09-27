"""Esquemas de entrada y vistas de solo lectura de facturación fiscal (plan T4.5).

Formato del rango: `NNN-NNN-NN-NNNNNNNN` (art. 10 de la investigación), donde los primeros tres
segmentos son el prefijo del punto de emisión autorizado y los últimos 8 dígitos son el
correlativo. `range_start`/`range_end` deben compartir el mismo prefijo; solo se valida que el
correlativo final de `range_start` sea numérico y menor o igual al de `range_end` (no se valida
la forma completa de los tres primeros segmentos más allá de que existan, ya que su composición
exacta depende del trámite ante el SAR de cada negocio, fuera del alcance de esta validación).
"""

from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


def _prefijo_y_correlativo(rango: str) -> tuple[str, int]:
    partes = rango.rsplit("-", 1)
    if len(partes) != 2 or not partes[1].isdigit():
        raise ValueError(f"'{rango}' no tiene el formato NNN-NNN-NN-NNNNNNNN")
    return partes[0], int(partes[1])


class FiscalAuthorizationInput(BaseModel):
    """Datos para registrar una autorización CAI."""

    model_config = ConfigDict(str_strip_whitespace=True)

    cai: str
    range_start: str
    range_end: str
    valid_until: date

    @field_validator("cai")
    @classmethod
    def _cai_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("el CAI no puede estar vacío")
        return v

    @field_validator("range_start", "range_end")
    @classmethod
    def _rango_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("el rango no puede estar vacío")
        return v

    @model_validator(mode="after")
    def _rango_valido(self) -> FiscalAuthorizationInput:
        prefijo_inicio, correlativo_inicio = _prefijo_y_correlativo(self.range_start)
        prefijo_fin, correlativo_fin = _prefijo_y_correlativo(self.range_end)
        if prefijo_inicio != prefijo_fin:
            raise ValueError("range_start y range_end deben compartir el mismo prefijo")
        if correlativo_inicio > correlativo_fin:
            raise ValueError("range_start no puede ser mayor que range_end")
        return self


@dataclass(frozen=True)
class FiscalAuthorizationView:
    """Vista de solo lectura de una autorización CAI."""

    id: int
    cai: str
    document_type: str
    range_start: str
    range_end: str
    valid_until: date
    next_correlative: int
    status: str


@dataclass(frozen=True)
class FiscalInvoiceView:
    """Vista de solo lectura de una factura fiscal emitida."""

    id: int
    sale_id: int
    authorization_id: int
    fiscal_number: str
    issued_at: datetime
