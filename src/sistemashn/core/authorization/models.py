"""Modelo de excepciones de permiso por usuario (`core_user_permission`, plan T1.1)."""

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base


class UserPermission(Base):
    """Override de un permiso para un usuario concreto (otorga o revoca sobre su perfil)."""

    __tablename__ = "core_user_permission"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("core_user.id", ondelete="CASCADE"), primary_key=True
    )
    permission_code: Mapped[str] = mapped_column(String, primary_key=True)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
