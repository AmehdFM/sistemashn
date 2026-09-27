"""Modelos de ajustes del negocio (`core_business`) y clave/valor genérico (`core_setting`)."""

from datetime import datetime

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime


class Business(Base):
    """Datos del negocio; fila única (`id=1`)."""

    __tablename__ = "core_business"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    legal_name: Mapped[str] = mapped_column(String, nullable=False)
    rtn: Mapped[str | None] = mapped_column(String(14), nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    prices_include_isv: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fiscal_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class Setting(Base):
    """Valor genérico clave/valor, serializado como JSON de un esquema Pydantic."""

    __tablename__ = "core_setting"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
