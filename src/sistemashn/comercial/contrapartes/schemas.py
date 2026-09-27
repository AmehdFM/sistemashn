"""Esquemas de entrada (Pydantic) y vistas de solo lectura de contrapartes (plan T3.1)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

from sistemashn.core.settings.schemas import _RTN_RE


class PartyKind(StrEnum):
    """Naturaleza de la contraparte."""

    PERSONA = "persona"
    NEGOCIO = "negocio"


class PartyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    kind: PartyKind
    name: str
    rtn: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_supplier: bool = False
    is_customer: bool = False
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("nombre de contraparte inválido: 1-200 caracteres")
        return v

    @field_validator("rtn")
    @classmethod
    def _rtn(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _RTN_RE.match(v):
            raise ValueError("el RTN debe tener 14 dígitos")
        return v

    @field_validator("phone", "email", "address", "notes")
    @classmethod
    def _texto_opcional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


@dataclass(frozen=True)
class PartyView:
    id: int
    kind: PartyKind
    name: str
    rtn: str | None
    phone: str | None
    email: str | None
    address: str | None
    is_supplier: bool
    is_customer: bool
    active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
