"""Esquemas Pydantic de ajustes: entrada/vista de negocio y validación de RTN."""

import re
from datetime import datetime

from pydantic import BaseModel, field_validator

_RTN_RE = re.compile(r"^\d{14}$")


class BusinessInput(BaseModel):
    """Datos editables del negocio (sin `fiscal_enabled`, que gestiona el módulo fiscal)."""

    name: str
    legal_name: str
    rtn: str | None = None
    address: str
    phone: str
    email: str
    prices_include_isv: bool = True

    @field_validator("rtn")
    @classmethod
    def _validar_rtn(cls, value: str | None) -> str | None:
        if value is not None and not _RTN_RE.match(value):
            raise ValueError("el RTN debe tener 14 dígitos")
        return value


class BusinessView(BaseModel):
    """Proyección de solo lectura de `Business`."""

    id: int
    name: str
    legal_name: str
    rtn: str | None
    address: str
    phone: str
    email: str
    logo_path: str | None
    prices_include_isv: bool
    fiscal_enabled: bool
    updated_at: datetime
