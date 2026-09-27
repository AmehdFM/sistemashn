"""Modelo del asistente de primer arranque (`core_installation`, fila única `id=1`)."""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime


class Installation(Base):
    """Estado del asistente de primer arranque de esta instalación."""

    __tablename__ = "core_installation"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[str] = mapped_column(String, nullable=False)
    vertical: Mapped[str] = mapped_column(String, nullable=False)
    setup_step: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
