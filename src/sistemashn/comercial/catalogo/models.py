"""Modelos del catálogo (`com_unit`, `com_category`, `com_product`, plan T2.1)."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money, Quantity, Rate, UtcDateTime


class Unit(Base):
    """Unidad de medida de un producto (p. ej. unidad, litro, kit)."""

    __tablename__ = "com_unit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    allows_fraction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Category(Base):
    """Categoría de producto."""

    __tablename__ = "com_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Product(Base):
    """Producto del catálogo comercial (repuesto u otro artículo vendible)."""

    __tablename__ = "com_product"
    __table_args__ = (
        CheckConstraint("sale_price >= 0", name="sale_price_no_negativo"),
        CheckConstraint("tax_rate IN (0, 1500, 1800)", name="tax_rate_valido"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_search: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("com_category.id"), nullable=True
    )
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_unit.id"), nullable=False)
    tax_rate: Mapped[object] = mapped_column(Rate(), nullable=False)
    sale_price: Mapped[object] = mapped_column(Money(), nullable=False)
    min_stock: Mapped[object] = mapped_column(Quantity(), nullable=False)
    is_kit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Foto del producto (T7.4); nombre de archivo relativo a `data_dir/productos/`.
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


from sistemashn.comercial.catalogo import kits as _kits  # noqa: E402,F401  (registra KitComponent)
