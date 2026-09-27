"""Modelo de auditoría: eventos append-only del Core.

`core_audit_event` nunca se actualiza ni se borra: es el historial de lo que
hizo cada usuario, y debe sobrevivir a cualquier cambio futuro sobre esos
usuarios (por eso `user_id` no lleva FK). Dos disparadores SQLite lo hacen
cumplir a nivel de base de datos.
"""

from datetime import datetime

from sqlalchemy import DDL, Index, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from sistemashn.core.db.base import Base
from sistemashn.core.db.types import UtcDateTime

_RAISE_APPEND_ONLY = "RAISE(ABORT, 'audit is append-only')"

# Sentencias DDL de los disparadores, expuestas para que la migración Alembic
# de la fase las reutilice literalmente (no debe haber dos definiciones distintas).
AUDIT_TRIGGERS_SQL: tuple[str, ...] = (
    f"""
    CREATE TRIGGER trg_core_audit_event_no_update
    BEFORE UPDATE ON core_audit_event
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
    f"""
    CREATE TRIGGER trg_core_audit_event_no_delete
    BEFORE DELETE ON core_audit_event
    BEGIN
        SELECT {_RAISE_APPEND_ONLY};
    END;
    """,
)


class AuditEvent(Base):
    """Un evento de auditoría inmutable."""

    __tablename__ = "core_audit_event"
    __table_args__ = (Index("ix_core_audit_event_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)
    # Sin FK a core_user a propósito: el historial de auditoría sobrevive a
    # cualquier cambio (incluida la eliminación) de los usuarios.
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str] = mapped_column(String, nullable=False, default="")
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)


for _sql in AUDIT_TRIGGERS_SQL:
    event.listen(
        AuditEvent.__table__,
        "after_create",
        DDL(_sql).execute_if(dialect="sqlite"),
    )
