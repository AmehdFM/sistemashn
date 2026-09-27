"""Modelo de usuario (`core_user`, plan T1.2). Solo el modelo; los servicios van aparte."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime


class User(Base):
    """Usuario del sistema. `profile_code` referencia un `ProfileDef` registrado."""

    __tablename__ = "core_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    profile_code: Mapped[str | None] = mapped_column(String, nullable=True)
    permissions_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


class LoginSession(Base):
    """Sesión de login activa o cerrada; `id` es un uuid4 en texto (T1.2)."""

    __tablename__ = "core_login_session"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("core_user.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class AuthFailure(Base):
    """Intento de login fallido; nunca guarda la contraseña, solo el usuario intentado."""

    __tablename__ = "core_auth_failure"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username_intentado: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)


class RecoveryCode(Base):
    """Código de recuperación de un solo uso; solo se guarda el hash argon2."""

    __tablename__ = "core_recovery_code"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    used_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RecoveryChallenge(Base):
    """Desafío de recuperación asistida por el vendedor (nonce de un solo uso)."""

    __tablename__ = "core_recovery_challenge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nonce: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
