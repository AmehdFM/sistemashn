"""Modelos de cotizaciones (`com_quote`, `com_quote_line`, plan T4.1)."""

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money, Quantity, Rate, UtcDateTime


class Quote(Base):
    """Encabezado de una cotización, con o sin apartado de inventario."""

    __tablename__ = "com_quote"
    __table_args__ = (
        CheckConstraint(
            "status IN ('abierta', 'convertida', 'cancelada', 'vencida')", name="status_valido"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_party.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_until: Mapped[date] = mapped_column(Date(), nullable=False)
    has_reservation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    subtotal: Mapped[object] = mapped_column(Money(), nullable=False)
    tax_total: Mapped[object] = mapped_column(Money(), nullable=False)
    total: Mapped[object] = mapped_column(Money(), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class QuoteLine(Base):
    """Línea de una cotización: un producto (o kit), cantidad y precio."""

    __tablename__ = "com_quote_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_quote.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), nullable=False)
    description_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[object] = mapped_column(Quantity(), nullable=False)
    unit_price: Mapped[object] = mapped_column(Money(), nullable=False)
    tax_rate: Mapped[object] = mapped_column(Rate(), nullable=False)
    line_subtotal: Mapped[object] = mapped_column(Money(), nullable=False)
    line_tax: Mapped[object] = mapped_column(Money(), nullable=False)
    line_total: Mapped[object] = mapped_column(Money(), nullable=False)
