"""Modelo de sonda para probar sesiones y el pipeline de migraciones (solo pruebas)."""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ProbeBase(DeclarativeBase):
    pass


class ProbeRecord(ProbeBase):
    __tablename__ = "probe_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    value: Mapped[str] = mapped_column(nullable=False)
    note: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
