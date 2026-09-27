"""Modelos de ajustes del negocio (`core_business`) y clave/valor genérico (`core_setting`)."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Rate, UtcDateTime

#: Valores por defecto de los ajustes de operación (Fase 7): una instalación nueva sin tocar
#: "Ajustes de operación" se comporta exactamente igual que el sistema ya probado en Fases 1-6.
DEFAULT_CASH_SESSION_REQUIRED = True
DEFAULT_BLOCK_SALE_WITHOUT_STOCK = True
DEFAULT_PRINT_RECEIPT_POLICY = "ask"
DEFAULT_CASHIER_SEES_OWN_SALES_TOTAL = True
DEFAULT_MAX_DISCOUNT_PERCENT = 0  # fracción (0.20 = 20%), misma convención que `tax_rate`
DEFAULT_CREDIT_DAYS = 30
DEFAULT_QUOTE_VALIDITY_DAYS = 8
DEFAULT_POS_SIMPLIFIED_MODE_ENABLED = True
DEFAULT_POS_EXIT_REQUIRES_MANAGER_AUTH = False
DEFAULT_SHOW_LOGO_IN_APP = True


class Business(Base):
    """Datos del negocio; fila única (`id=1`)."""

    __tablename__ = "core_business"
    __table_args__ = (
        CheckConstraint(
            "print_receipt_policy IN ('auto', 'ask', 'never')", name="print_receipt_policy_valida"
        ),
        CheckConstraint("default_credit_days > 0", name="default_credit_days_positivo"),
        CheckConstraint(
            "default_quote_validity_days > 0", name="default_quote_validity_days_positivo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    legal_name: Mapped[str] = mapped_column(String, nullable=False)
    rtn: Mapped[str | None] = mapped_column(String(14), nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    prices_include_isv: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fiscal_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)

    # -- Ajustes de operación (Fase 7): ver docs/superpowers/plans/fase-7-mejoras-ui-ux.md T7.2 --
    cash_session_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_CASH_SESSION_REQUIRED
    )
    block_sale_without_stock: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_BLOCK_SALE_WITHOUT_STOCK
    )
    print_receipt_policy: Mapped[str] = mapped_column(
        String(10), nullable=False, default=DEFAULT_PRINT_RECEIPT_POLICY
    )
    cashier_sees_own_sales_total: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_CASHIER_SEES_OWN_SALES_TOTAL
    )
    max_discount_percent: Mapped[object] = mapped_column(
        Rate(), nullable=False, default=DEFAULT_MAX_DISCOUNT_PERCENT
    )
    default_credit_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_CREDIT_DAYS
    )
    default_quote_validity_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_QUOTE_VALIDITY_DAYS
    )
    pos_simplified_mode_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_POS_SIMPLIFIED_MODE_ENABLED
    )
    pos_exit_requires_manager_auth: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_POS_EXIT_REQUIRES_MANAGER_AUTH
    )
    show_logo_in_app: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=DEFAULT_SHOW_LOGO_IN_APP
    )


class Setting(Base):
    """Valor genérico clave/valor, serializado como JSON de un esquema Pydantic."""

    __tablename__ = "core_setting"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
