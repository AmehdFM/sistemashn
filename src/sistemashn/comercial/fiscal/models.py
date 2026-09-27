"""Modelos de facturación fiscal (CAI), plan T4.5: implementados pero deshabilitados por
defecto (`core_business.fiscal_enabled = False`). No afirman cumplimiento fiscal; ver
`docs/investigacion-facturacion-honduras.md`."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime


class FiscalAuthorization(Base):
    """Autorización CAI registrada para un tipo de documento, con su rango y vigencia."""

    __tablename__ = "com_fiscal_authorization"
    __table_args__ = (
        CheckConstraint("document_type IN ('factura')", name="document_type_valido"),
        CheckConstraint("status IN ('activa', 'agotada', 'vencida')", name="fiscal_status_valido"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cai: Mapped[str] = mapped_column(String(37), unique=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(20), nullable=False)
    range_start: Mapped[str] = mapped_column(String(20), nullable=False)
    range_end: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_until: Mapped[date] = mapped_column(Date(), nullable=False)
    next_correlative: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)


class FiscalInvoice(Base):
    """Factura fiscal emitida para una venta (1:1). `sale_id` no lleva FK real a `com_sale`
    porque ese módulo (`comercial/ventas/`) todavía no existe en el repositorio: se agrega la
    restricción cuando exista, si se decide necesaria."""

    __tablename__ = "com_fiscal_invoice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    authorization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("com_fiscal_authorization.id"), nullable=False
    )
    fiscal_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
