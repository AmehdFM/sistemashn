"""Esquemas Pydantic de ajustes: entrada/vista de negocio y validación de RTN."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

from sistemashn.core.settings.models import (
    DEFAULT_BLOCK_SALE_WITHOUT_STOCK,
    DEFAULT_CASH_SESSION_REQUIRED,
    DEFAULT_CASHIER_SEES_OWN_SALES_TOTAL,
    DEFAULT_CREDIT_DAYS,
    DEFAULT_MAX_DISCOUNT_PERCENT,
    DEFAULT_POS_EXIT_REQUIRES_MANAGER_AUTH,
    DEFAULT_POS_SIMPLIFIED_MODE_ENABLED,
    DEFAULT_PRINT_RECEIPT_POLICY,
    DEFAULT_QUOTE_VALIDITY_DAYS,
    DEFAULT_SHOW_LOGO_IN_APP,
)

_RTN_RE = re.compile(r"^\d{14}$")
PrintReceiptPolicy = Literal["auto", "ask", "never"]


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
    cash_session_required: bool
    block_sale_without_stock: bool
    print_receipt_policy: PrintReceiptPolicy
    cashier_sees_own_sales_total: bool
    max_discount_percent: Decimal
    default_credit_days: int
    default_quote_validity_days: int
    pos_simplified_mode_enabled: bool
    pos_exit_requires_manager_auth: bool
    show_logo_in_app: bool


class OperationSettingsInput(BaseModel):
    """Ajustes de operación editables desde "Ajustes de operación" (Fase 7, T7.2/T7.6).

    Separado de `BusinessInput` (identidad/contacto del negocio) porque cambia con otra
    frecuencia y lo edita otra pantalla; ambos actualizan la misma fila de `core_business`.
    """

    cash_session_required: bool = DEFAULT_CASH_SESSION_REQUIRED
    block_sale_without_stock: bool = DEFAULT_BLOCK_SALE_WITHOUT_STOCK
    print_receipt_policy: PrintReceiptPolicy = DEFAULT_PRINT_RECEIPT_POLICY
    cashier_sees_own_sales_total: bool = DEFAULT_CASHIER_SEES_OWN_SALES_TOTAL
    max_discount_percent: Decimal = Decimal(DEFAULT_MAX_DISCOUNT_PERCENT)
    default_credit_days: int = DEFAULT_CREDIT_DAYS
    default_quote_validity_days: int = DEFAULT_QUOTE_VALIDITY_DAYS
    pos_simplified_mode_enabled: bool = DEFAULT_POS_SIMPLIFIED_MODE_ENABLED
    pos_exit_requires_manager_auth: bool = DEFAULT_POS_EXIT_REQUIRES_MANAGER_AUTH
    show_logo_in_app: bool = DEFAULT_SHOW_LOGO_IN_APP

    @field_validator("max_discount_percent")
    @classmethod
    def _validar_descuento(cls, value: Decimal) -> Decimal:
        # Fracción (0.20 = 20%), misma convención que `tax_rate` (Rate, ADR-002), no 0-100.
        if value < 0 or value > 1:
            raise ValueError("el descuento máximo debe estar entre 0 y 1 (p. ej. 0.20 = 20%)")
        return value

    @field_validator("default_credit_days", "default_quote_validity_days")
    @classmethod
    def _validar_dias(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("los días deben ser un número positivo")
        return value
