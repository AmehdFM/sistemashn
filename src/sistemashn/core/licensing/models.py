"""Modelo de licencia instalada (T1.4): historial de licencias guardadas localmente."""

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime


class InstalledLicense(Base):
    """Una fila por cada licencia instalada; la vigente es la de `installed_at` más reciente.

    `install()` nunca borra filas anteriores: conserva el historial completo.
    """

    __tablename__ = "core_license"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    raw_text: Mapped[str] = mapped_column(nullable=False)
    license_id: Mapped[str] = mapped_column(nullable=False)
    installed_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
