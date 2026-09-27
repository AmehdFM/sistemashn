"""Pruebas de auditoría (T1.3): registro append-only y consulta paginada."""

from datetime import UTC, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from sistemashn.core.audit.models import AuditEvent
from sistemashn.core.audit.service import (
    AuditEventView,
    AuditQuery,
    AuditQueryService,
    audit,
)
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import PermissionDenied

ACTOR = Actor(user_id=7, username="ana", is_admin=False, session_id="sesion-1")


class _AutorizadorPermisivo:
    def require(self, session, actor, code) -> None:
        pass


class _AutorizadorQueNiega:
    def require(self, session, actor, code) -> None:
        raise PermissionDenied(f"{actor.username} no tiene {code}")


def test_audit_guarda_evento_con_actor_y_hora_del_reloj(session_factory, clock, now) -> None:
    with session_scope(session_factory) as session:
        evento = audit(
            session,
            ACTOR,
            "core.usuarios.crear",
            entity_type="core_user",
            entity_id="42",
            summary="creó al usuario 42",
            clock=clock,
        )
        assert evento.id is not None

    with session_scope(session_factory, readonly=True) as session:
        guardado = session.get(AuditEvent, evento.id)
        assert guardado is not None
        assert guardado.user_id == ACTOR.user_id
        assert guardado.username == ACTOR.username
        assert guardado.session_id == ACTOR.session_id
        assert guardado.action == "core.usuarios.crear"
        assert guardado.entity_type == "core_user"
        assert guardado.entity_id == "42"
        assert guardado.occurred_at.replace(tzinfo=UTC) == now


def test_rollback_de_transaccion_de_negocio_elimina_tambien_el_evento(session_factory) -> None:
    with pytest.raises(RuntimeError), session_scope(session_factory) as session:
        audit(session, ACTOR, "core.usuarios.crear", summary="no debe sobrevivir")
        raise RuntimeError("fallo simulado en la operación de negocio")

    with session_scope(session_factory, readonly=True) as session:
        total = session.query(AuditEvent).count()
        assert total == 0


def test_update_directo_falla_por_el_disparador(session_factory) -> None:
    with session_scope(session_factory) as session:
        evento = audit(session, ACTOR, "core.usuarios.crear", summary="x")
        evento_id = evento.id

    with (
        pytest.raises(IntegrityError, match="audit is append-only"),
        session_scope(session_factory) as session,
    ):
        session.execute(
            text("UPDATE core_audit_event SET summary = 'hackeado' WHERE id = :id"),
            {"id": evento_id},
        )


def test_delete_directo_falla_por_el_disparador(session_factory) -> None:
    with session_scope(session_factory) as session:
        evento = audit(session, ACTOR, "core.usuarios.crear", summary="x")
        evento_id = evento.id

    with (
        pytest.raises(IntegrityError, match="audit is append-only"),
        session_scope(session_factory) as session,
    ):
        session.execute(
            text("DELETE FROM core_audit_event WHERE id = :id"),
            {"id": evento_id},
        )


def test_detalle_con_decimal_y_datetime_serializa(session_factory, now) -> None:
    detalle = {
        "monto": Decimal("125.50"),
        "cuando": now,
        "anidado": {"cantidad": Decimal("3")},
    }
    with session_scope(session_factory) as session:
        evento = audit(session, ACTOR, "comercial.venta.crear", detail=detalle)
        evento_id = evento.id

    with session_scope(session_factory, readonly=True) as session:
        guardado = session.get(AuditEvent, evento_id)
        assert guardado is not None
        assert guardado.detail_json is not None
        assert '"125.50"' in guardado.detail_json
        assert now.isoformat() in guardado.detail_json


def test_clave_prohibida_anidada_lanza_value_error(session_factory) -> None:
    detalle = {"usuario": "ana", "credenciales": {"password": "secreta"}}
    with pytest.raises(ValueError, match="password"), session_scope(session_factory) as session:
        audit(session, ACTOR, "core.usuarios.crear", detail=detalle)


def _sembrar_eventos(session_factory, now) -> None:
    momentos = [now - timedelta(days=2), now - timedelta(days=1), now]
    with session_scope(session_factory) as session:
        audit(
            session,
            ACTOR,
            "core.usuarios.crear",
            entity_type="core_user",
            entity_id="1",
            clock=lambda: momentos[0],
        )
        audit(
            session,
            ACTOR,
            "core.usuarios.actualizar",
            entity_type="core_user",
            entity_id="1",
            clock=lambda: momentos[1],
        )
        audit(
            session,
            ACTOR,
            "comercial.venta.crear",
            entity_type="comercial_venta",
            entity_id="99",
            clock=lambda: momentos[2],
        )


def test_list_pagina_con_filtros_y_total_correcto(session_factory, now) -> None:
    _sembrar_eventos(session_factory, now)
    servicio = AuditQueryService(session_factory, _AutorizadorPermisivo())

    resultado = servicio.list(ACTOR, AuditQuery(action_prefix="core.usuarios."))
    assert resultado.total == 2
    assert all(isinstance(item, AuditEventView) for item in resultado.items)
    # orden desc por occurred_at: primero el más reciente (actualizar)
    assert [item.action for item in resultado.items] == [
        "core.usuarios.actualizar",
        "core.usuarios.crear",
    ]

    por_entidad = servicio.list(ACTOR, AuditQuery(entity_type="comercial_venta", entity_id="99"))
    assert por_entidad.total == 1
    assert por_entidad.items[0].action == "comercial.venta.crear"

    por_rango = servicio.list(
        ACTOR,
        AuditQuery(since=now - timedelta(hours=12), until=now + timedelta(hours=1)),
    )
    assert por_rango.total == 1
    assert por_rango.items[0].action == "comercial.venta.crear"

    paginado = servicio.list(ACTOR, AuditQuery(), page=1, page_size=2)
    assert paginado.total == 3
    assert len(paginado.items) == 2
    assert paginado.pages == 2


def test_list_lanza_permission_denied_si_el_autorizador_lo_hace(session_factory, now) -> None:
    _sembrar_eventos(session_factory, now)
    servicio = AuditQueryService(session_factory, _AutorizadorQueNiega())

    with pytest.raises(PermissionDenied):
        servicio.list(ACTOR, AuditQuery())
