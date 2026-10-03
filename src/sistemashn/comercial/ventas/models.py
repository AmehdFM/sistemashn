"""Modelos de ventas (`com_sale`, `com_sale_line`, `com_sale_payment`, plan T4.2)."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money, Quantity, Rate, UnitCost, UtcDateTime


class Sale(Base):
    """Encabezado de una venta confirmada (comprobante interno)."""

    __tablename__ = "com_sale"
    __table_args__ = (CheckConstraint("status IN ('confirmada', 'anulada')", name="status_valido"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    quote_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("com_quote.id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_party.id"), nullable=True
    )
    sold_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    subtotal: Mapped[object] = mapped_column(Money(), nullable=False)
    tax_total: Mapped[object] = mapped_column(Money(), nullable=False)
    total: Mapped[object] = mapped_column(Money(), nullable=False)
    paid_amount: Mapped[object] = mapped_column(Money(), nullable=False)
    change_amount: Mapped[object] = mapped_column(Money(), nullable=False)
    credit_amount: Mapped[object] = mapped_column(Money(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cash_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_cash_session.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class SaleLine(Base):
    """Línea de una venta: un producto (o componente de kit), cantidad y precio.

    `kit_component_of` guarda el `line_no` (no el `id`) de la línea de kit que generó esta línea
    de componente: es una referencia lógica dentro de la misma venta, sin FK propia porque
    `line_no` no es único por sí solo (solo lo es junto a `sale_id`). Las líneas de componente no
    tienen precio propio: el precio de venta vive únicamente en la línea del kit
    (`unit_price`/`tax_rate`/`line_total` en cero), su único aporte es el costo aplicado
    (`unit_cost_snapshot`) para el cálculo de utilidad.
    """

    __tablename__ = "com_sale_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_sale.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), nullable=False)
    description_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[object] = mapped_column(Quantity(), nullable=False)
    unit_price: Mapped[object] = mapped_column(Money(), nullable=False)
    tax_rate: Mapped[object] = mapped_column(Rate(), nullable=False)
    line_subtotal: Mapped[object] = mapped_column(Money(), nullable=False)
    line_tax: Mapped[object] = mapped_column(Money(), nullable=False)
    line_total: Mapped[object] = mapped_column(Money(), nullable=False)
    presentation_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_cost_snapshot: Mapped[object] = mapped_column(UnitCost(), nullable=False)
    kit_component_of: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Cantidad vendida sin stock disponible al momento (T7.3, `block_sale_without_stock=False`).
    backorder_qty: Mapped[object] = mapped_column(Quantity(), nullable=False, default=0)


class SalePayment(Base):
    """Pago aplicado a una venta al momento de confirmarla."""

    __tablename__ = "com_sale_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_sale.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[object] = mapped_column(Money(), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(60), nullable=True)
