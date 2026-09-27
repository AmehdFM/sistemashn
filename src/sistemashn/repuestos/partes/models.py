"""Modelos de partes y equivalencias (`rep_part`, `rep_equivalence_group`, plan T2.4)."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime


class EquivalenceGroup(Base):
    """Grupo de equivalencia entre partes: solo genera ids agrupadores."""

    __tablename__ = "rep_equivalence_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class Part(Base):
    """Datos de repuesto de un producto comercial: número de parte, fabricante y origen."""

    __tablename__ = "rep_part"
    __table_args__ = (CheckConstraint("origin IN ('original', 'generico')", name="origin_valido"),)

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("com_product.id", ondelete="RESTRICT"), primary_key=True
    )
    part_number: Mapped[str] = mapped_column(String(80), nullable=False)
    part_number_search: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    equivalence_group_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("rep_equivalence_group.id"), nullable=True, index=True
    )
