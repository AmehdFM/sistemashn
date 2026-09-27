"""Modelo de contraparte (`com_party`, plan T3.1)."""

from datetime import datetime

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime


class Party(Base):
    """Persona o negocio que puede ser proveedor y/o cliente."""

    __tablename__ = "com_party"
    __table_args__ = (Index("ix_com_party_rtn", "rtn"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_search: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    rtn: Mapped[str | None] = mapped_column(String(14), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_supplier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_customer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
