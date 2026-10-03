"""Modelos de compras (`com_purchase`, `com_purchase_line`, `com_purchase_payment`,
`com_supplier_price`, plan T3.2)."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money, Quantity, Rate, UnitCost, UtcDateTime


class Purchase(Base):
    """Encabezado de una compra confirmada a un proveedor."""

    __tablename__ = "com_purchase"
    __table_args__ = (CheckConstraint("status IN ('confirmada', 'anulada')", name="status_valido"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_party.id"), nullable=False)
    supplier_invoice_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    subtotal: Mapped[object] = mapped_column(Money(), nullable=False)
    tax_total: Mapped[object] = mapped_column(Money(), nullable=False)
    total: Mapped[object] = mapped_column(Money(), nullable=False)
    paid_initial: Mapped[object] = mapped_column(Money(), nullable=False)
    credit_amount: Mapped[object] = mapped_column(Money(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class PurchaseLine(Base):
    """Línea de una compra: un producto, cantidad y costo unitario."""

    __tablename__ = "com_purchase_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_purchase.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), nullable=False)
    description_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    qty: Mapped[object] = mapped_column(Quantity(), nullable=False)
    unit_cost: Mapped[object] = mapped_column(UnitCost(), nullable=False)
    tax_rate: Mapped[object] = mapped_column(Rate(), nullable=False)
    line_subtotal: Mapped[object] = mapped_column(Money(), nullable=False)
    line_tax: Mapped[object] = mapped_column(Money(), nullable=False)
    line_total: Mapped[object] = mapped_column(Money(), nullable=False)
    presentation_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)


class PurchasePayment(Base):
    """Pago aplicado a una compra al momento de confirmarla."""

    __tablename__ = "com_purchase_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_purchase.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[object] = mapped_column(Money(), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(60), nullable=True)


class SupplierPrice(Base):
    """Histórico de costos por proveedor y producto: una fila por línea de compra, nunca se
    actualiza ni se borra."""

    __tablename__ = "com_supplier_price"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_party.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), nullable=False)
    unit_cost: Mapped[object] = mapped_column(UnitCost(), nullable=False)
    purchase_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_purchase.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
