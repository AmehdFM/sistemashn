"""Atributos y presentaciones de Ferretería sobre el SKU comercial."""

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Money


class FerItem(Base):
    __tablename__ = "fer_item"

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), primary_key=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    family: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    specs: Mapped[str | None] = mapped_column(Text, nullable=True)


class FerPack(Base):
    __tablename__ = "fer_pack"
    __table_args__ = (
        CheckConstraint("factor_numerator > 0", name="factor_numerator_positivo"),
        CheckConstraint("factor_denominator > 0", name="factor_denominator_positivo"),
        CheckConstraint("price IS NULL OR price >= 0", name="price_no_negativo"),
        UniqueConstraint("product_id", "label", name="uq_fer_pack_product_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("com_product.id"), nullable=False, index=True
    )
    code: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # El cociente entero evita que SQLite convierta el factor a float.
    factor_numerator: Mapped[int] = mapped_column(Integer, nullable=False)
    factor_denominator: Mapped[int] = mapped_column(Integer, nullable=False)
    permits_fraction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price: Mapped[object | None] = mapped_column(Money(), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
