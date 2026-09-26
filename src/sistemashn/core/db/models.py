"""Modelo final de la sonda, sincronizado con la migración 0002."""

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProbeRecord(Base):
    __tablename__ = "probe_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")
