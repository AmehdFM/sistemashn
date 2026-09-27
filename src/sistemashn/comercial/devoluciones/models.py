"""Modelos de devoluciones de cliente y a proveedor (plan T5.2/T5.3)."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money, Quantity, UtcDateTime


class CustomerReturn(Base):
    """Devolución de una línea de venta, total o parcial."""

    __tablename__ = "com_customer_return"
    __table_args__ = (
        CheckConstraint("condition IN ('vendible', 'no_vendible')", name="condition_valida"),
        CheckConstraint(
            "resolution IN ('reembolso', 'cambio', 'saldo_a_favor')", name="resolution_valida"
        ),
        CheckConstraint(
            "sale_line_id IS NOT NULL "
            "OR (product_id IS NOT NULL AND unit_price_override IS NOT NULL)",
            name="sin_comprobante_valida",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: Nulo en una devolución "sin comprobante" (T7.3): en ese caso `product_id` y
    #: `unit_price_override` traen los datos que normalmente vendrían de la línea de venta.
    sale_line_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_sale_line.id"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_product.id"), nullable=True
    )
    unit_price_override: Mapped[object | None] = mapped_column(Money(), nullable=True)
    qty: Mapped[object] = mapped_column(Quantity(), nullable=False)
    condition: Mapped[str] = mapped_column(String(20), nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[object] = mapped_column(Money(), nullable=False)
    new_sale_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_sale.id"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class SupplierReturn(Base):
    """Devolución de una línea de compra a su proveedor, total o parcial."""

    __tablename__ = "com_supplier_return"
    __table_args__ = (
        CheckConstraint(
            "resolution IN ('reemplazo', 'reembolso', 'credito_futuro')",
            name="resolution_valida",
        ),
        CheckConstraint(
            "purchase_line_id IS NOT NULL "
            "OR (product_id IS NOT NULL AND unit_price_override IS NOT NULL)",
            name="sin_comprobante_valida",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: Nulo en una devolución "sin comprobante" (T7.3): en ese caso `product_id` y
    #: `unit_price_override` traen los datos que normalmente vendrían de la línea de compra.
    purchase_line_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_purchase_line.id"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_product.id"), nullable=True
    )
    unit_price_override: Mapped[object | None] = mapped_column(Money(), nullable=True)
    qty: Mapped[object] = mapped_column(Quantity(), nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[object] = mapped_column(Money(), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
