"""Esquemas de entrada (Pydantic) y vistas de solo lectura del catálogo (plan T2.1)."""

from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

_TASAS_VALIDAS = {Decimal("0"), Decimal("0.15"), Decimal("0.18")}


class UnitInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str
    name: str
    allows_fraction: bool = False

    @field_validator("code")
    @classmethod
    def _codigo_no_vacio(cls, v: str) -> str:
        v = v.strip().upper()
        if not v or len(v) > 20:
            raise ValueError("código de unidad inválido: 1-20 caracteres")
        return v

    @field_validator("name")
    @classmethod
    def _nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("nombre de unidad requerido")
        return v


class CategoryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str

    @field_validator("name")
    @classmethod
    def _nombre_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("nombre de categoría inválido: 1-100 caracteres")
        return v


class ProductInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str
    barcode: str | None = None
    name: str
    description: str | None = None
    category_id: int | None = None
    unit_id: int
    tax_rate: Decimal
    sale_price: Decimal
    min_stock: Decimal = Decimal("0")
    is_kit: bool = False
    active: bool = True

    @field_validator("code")
    @classmethod
    def _codigo(cls, v: str) -> str:
        v = v.strip().upper()
        if not v or len(v) > 40:
            raise ValueError("código de producto inválido: 1-40 caracteres")
        return v

    @field_validator("barcode")
    @classmethod
    def _codigo_barras(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("name")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("nombre de producto inválido: 1-200 caracteres")
        return v

    @field_validator("sale_price")
    @classmethod
    def _precio(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("el precio de venta no puede ser negativo")
        return v

    @field_validator("min_stock")
    @classmethod
    def _minimo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("el stock mínimo no puede ser negativo")
        return v

    @field_validator("tax_rate")
    @classmethod
    def _tasa(cls, v: Decimal) -> Decimal:
        if v not in _TASAS_VALIDAS:
            raise ValueError("tasa de ISV inválida: debe ser 0, 0.15 o 0.18")
        return v


@dataclass(frozen=True)
class UnitView:
    id: int
    code: str
    name: str
    allows_fraction: bool
    active: bool


@dataclass(frozen=True)
class CategoryView:
    id: int
    name: str
    active: bool


@dataclass(frozen=True)
class ProductView:
    id: int
    code: str
    barcode: str | None
    name: str
    description: str | None
    category_id: int | None
    unit_id: int
    tax_rate: Decimal
    sale_price: Decimal
    min_stock: Decimal
    is_kit: bool
    active: bool
    on_hand: Decimal
    reserved: Decimal
    available: Decimal
    avg_cost: Decimal | None
    image_path: str | None
