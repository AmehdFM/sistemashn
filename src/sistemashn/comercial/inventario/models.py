"""Modelos de existencias e historial de movimientos (`com_stock`, `com_stock_movement`, T2.2)."""

from datetime import datetime

from sqlalchemy import DDL, CheckConstraint, ForeignKey, Index, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Quantity, UnitCost, UtcDateTime

_RAISE_APPEND_ONLY = "RAISE(ABORT, 'stock movement is append-only')"

# Igual que en `core.audit.models`: la migración de la fase reutiliza estas mismas sentencias.
STOCK_MOVEMENT_TRIGGERS_SQL: tuple[str, ...] = (
    f"""
    CREATE TRIGGER trg_com_stock_movement_no_update
    BEFORE UPDATE ON com_stock_movement
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
    f"""
    CREATE TRIGGER trg_com_stock_movement_no_delete
    BEFORE DELETE ON com_stock_movement
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
)


class Stock(Base):
    """Existencias vigentes de un producto no-kit (una fila por producto)."""

    __tablename__ = "com_stock"
    __table_args__ = (
        CheckConstraint("on_hand >= 0", name="on_hand_no_negativo"),
        CheckConstraint("reserved >= 0", name="reserved_no_negativo"),
        CheckConstraint("unsellable >= 0", name="unsellable_no_negativo"),
        CheckConstraint("reserved <= on_hand", name="reserved_no_mayor_on_hand"),
    )

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), primary_key=True)
    on_hand: Mapped[object] = mapped_column(Quantity(), nullable=False, default=0)
    reserved: Mapped[object] = mapped_column(Quantity(), nullable=False, default=0)
    unsellable: Mapped[object] = mapped_column(Quantity(), nullable=False, default=0)
    avg_cost: Mapped[object] = mapped_column(UnitCost(), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class StockMovement(Base):
    """Movimiento inmutable del libro de inventario (una fila por operación)."""

    __tablename__ = "com_stock_movement"
    __table_args__ = (Index("ix_com_stock_movement_product", "product_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    d_on_hand: Mapped[object] = mapped_column(Quantity(), nullable=False, default=0)
    d_reserved: Mapped[object] = mapped_column(Quantity(), nullable=False, default=0)
    d_unsellable: Mapped[object] = mapped_column(Quantity(), nullable=False, default=0)
    unit_cost: Mapped[object | None] = mapped_column(UnitCost(), nullable=True)
    avg_cost_after: Mapped[object] = mapped_column(UnitCost(), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


for _sql in STOCK_MOVEMENT_TRIGGERS_SQL:
    event.listen(
        StockMovement.__table__,
        "after_create",
        DDL(_sql).execute_if(dialect="sqlite"),
    )
