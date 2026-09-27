"""Registro y consulta de auditoría (append-only, misma sesión que el negocio)."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.audit.models import AuditEvent
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.db.text import LIKE_ESCAPE, escape_like
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.pagination import Page, normalize_page

# Claves que nunca deben terminar en el detalle de un evento de auditoría,
# a cualquier nivel de anidación (listas y dicts).
_FORBIDDEN_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "new_password",
        "recovery_code",
        "token",
        "private_key",
    }
)


def _default_clock() -> datetime:
    return datetime.now(UTC)


class _AuditJSONEncoder(json.JSONEncoder):
    """Encoder de `detail` con soporte para tipos de dominio comunes."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime | date):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


def _check_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(key, str) and key.lower() in _FORBIDDEN_KEYS:
                raise ValueError(f"clave prohibida en detalle de auditoría: {key!r}")
            _check_forbidden_keys(val)
    elif isinstance(value, list | tuple):
        for item in value:
            _check_forbidden_keys(item)


def _serialize_detail(detail: dict[str, Any] | None) -> str | None:
    if detail is None:
        return None
    _check_forbidden_keys(detail)
    return json.dumps(detail, cls=_AuditJSONEncoder, separators=(",", ":"), sort_keys=True)


def audit(
    session: Session,
    actor: Actor,
    action: str,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    summary: str = "",
    detail: dict[str, Any] | None = None,
    clock: Callable[[], datetime] = _default_clock,
) -> AuditEvent:
    """Registra un evento de auditoría en `session`, sin hacer commit propio.

    Si la transacción de negocio hace rollback, el evento se va con ella: por
    eso `audit` nunca abre ni cierra su propia transacción.
    """
    evento = AuditEvent(
        occurred_at=clock(),
        user_id=actor.user_id,
        username=actor.username,
        session_id=actor.session_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        detail_json=_serialize_detail(detail),
    )
    session.add(evento)
    session.flush()
    return evento


@dataclass(frozen=True)
class AuditQuery:
    """Filtros para `AuditQueryService.list`; todos opcionales."""

    since: datetime | None = None
    until: datetime | None = None
    user_id: int | None = None
    action_prefix: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None


@dataclass(frozen=True)
class AuditEventView:
    """Proyección de solo lectura de un `AuditEvent`, con `detail` ya parseado."""

    id: int
    occurred_at: datetime
    user_id: int | None
    username: str
    session_id: str
    action: str
    entity_type: str | None
    entity_id: str | None
    summary: str
    detail: dict[str, Any] | None


class Authorizer(Protocol):
    """Lo mínimo que `AuditQueryService` necesita del autorizador del Core."""

    def require(self, session: Session, actor: Actor, code: str) -> None: ...


class AuditQueryService:
    """Consulta paginada de eventos de auditoría, protegida por permiso."""

    def __init__(self, factory: sessionmaker[Session], authorizer: Authorizer) -> None:
        self._factory = factory
        self._authorizer = authorizer

    def list(
        self,
        actor: Actor,
        query: AuditQuery,
        page: int = 1,
        page_size: int = 50,
    ) -> Page[AuditEventView]:
        def _operacion(session: Session) -> Page[AuditEventView]:
            self._authorizer.require(session, actor, "core.auditoria.ver")
            page_num, size, offset = normalize_page(page, page_size)

            filtros = []
            if query.since is not None:
                filtros.append(AuditEvent.occurred_at >= query.since)
            if query.until is not None:
                filtros.append(AuditEvent.occurred_at <= query.until)
            if query.user_id is not None:
                filtros.append(AuditEvent.user_id == query.user_id)
            if query.action_prefix is not None:
                filtros.append(
                    AuditEvent.action.like(
                        f"{escape_like(query.action_prefix)}%", escape=LIKE_ESCAPE
                    )
                )
            if query.entity_type is not None:
                filtros.append(AuditEvent.entity_type == query.entity_type)
            if query.entity_id is not None:
                filtros.append(AuditEvent.entity_id == query.entity_id)

            base = select(AuditEvent).where(*filtros)
            total = session.scalar(select(func.count()).select_from(base.subquery())) or 0

            filas = session.scalars(
                base.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
                .offset(offset)
                .limit(size)
            ).all()

            items = [
                AuditEventView(
                    id=fila.id,
                    occurred_at=fila.occurred_at,
                    user_id=fila.user_id,
                    username=fila.username,
                    session_id=fila.session_id,
                    action=fila.action,
                    entity_type=fila.entity_type,
                    entity_id=fila.entity_id,
                    summary=fila.summary,
                    detail=json.loads(fila.detail_json) if fila.detail_json else None,
                )
                for fila in filas
            ]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self._factory, _operacion, readonly=True)
