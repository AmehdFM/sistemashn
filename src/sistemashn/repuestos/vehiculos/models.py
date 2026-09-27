"""Modelos de vehículos y compatibilidad (`rep_vehicle_make`, `rep_vehicle_model`,
`rep_compatibility`, plan T2.4)."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base


class VehicleMake(Base):
    """Marca de vehículo (p. ej. Toyota)."""

    __tablename__ = "rep_vehicle_make"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class VehicleModel(Base):
    """Modelo de vehículo, asociado a una marca."""

    __tablename__ = "rep_vehicle_model"
    __table_args__ = (UniqueConstraint("make_id", "name", name="uq_rep_vehicle_model_make_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    make_id: Mapped[int] = mapped_column(Integer, ForeignKey("rep_vehicle_make.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)


class Compatibility(Base):
    """Compatibilidad de un producto con un modelo de vehículo en un rango de años."""

    __tablename__ = "rep_compatibility"
    __table_args__ = (
        CheckConstraint("year_from <= year_to", name="year_from_no_mayor_year_to"),
        CheckConstraint("year_from BETWEEN 1950 AND 2100", name="year_from_valido"),
        CheckConstraint("year_to BETWEEN 1950 AND 2100", name="year_to_valido"),
        UniqueConstraint(
            "product_id", "model_id", "year_from", "year_to", name="uq_rep_compatibility"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("com_product.id", ondelete="RESTRICT"), nullable=False
    )
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rep_vehicle_model.id"), nullable=False
    )
    year_from: Mapped[int] = mapped_column(Integer, nullable=False)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False)
