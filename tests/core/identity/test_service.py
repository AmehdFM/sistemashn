"""Pruebas de IdentityService: alta, edición, autenticación y sesiones (T1.2)."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from sistemashn.core.audit.models import AuditEvent
from sistemashn.core.authorization.actor import SYSTEM_ACTOR, Actor
from sistemashn.core.errors import AuthenticationError, PermissionDenied, ValidationError
from sistemashn.core.identity.models import AuthFailure, LoginSession, User
from sistemashn.core.identity.passwords import verify_password

CLAVE = "clave1234"


def _actor(user_id: int, username: str = "u", is_admin: bool = False) -> Actor:
    return Actor(user_id=user_id, username=username, is_admin=is_admin, session_id="s1")


# --- alta de usuarios -------------------------------------------------------------


def test_create_user_normaliza_username_y_hashea_password(identity_service, session_factory):
    user_id = identity_service.create_user(SYSTEM_ACTOR, "  ANA.Lopez ", "Ana López", CLAVE)
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user.username == "ana.lopez"
        assert user.password_hash != CLAVE
        assert verify_password(user.password_hash, CLAVE)


def test_create_user_username_duplicado_falla(identity_service):
    identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    with pytest.raises(ValidationError):
        identity_service.create_user(SYSTEM_ACTOR, "ANA", "Ana Otra", CLAVE)


def test_create_user_username_invalido_falla(identity_service):
    with pytest.raises(ValidationError):
        identity_service.create_user(SYSTEM_ACTOR, "an", "Ana", CLAVE)
    with pytest.raises(ValidationError):
        identity_service.create_user(SYSTEM_ACTOR, "usuario invalido!", "Ana", CLAVE)


def test_no_admin_no_puede_crear_admin(identity_service):
    empleado_id = identity_service.create_user(
        SYSTEM_ACTOR, "empleado", "Empleado", CLAVE, profile_code="administrador"
    )
    actor_empleado = _actor(empleado_id, "empleado")
    with pytest.raises(PermissionDenied):
        identity_service.create_user(
            actor_empleado, "nuevoadmin", "Nuevo Admin", CLAVE, is_admin=True
        )


def test_admin_puede_crear_admin(identity_service, session_factory):
    admin_id = identity_service.create_user(
        SYSTEM_ACTOR, "admin1", "Admin Uno", CLAVE, is_admin=True
    )
    actor_admin = _actor(admin_id, "admin1", is_admin=True)
    nuevo_id = identity_service.create_user(
        actor_admin, "admin2", "Admin Dos", CLAVE, is_admin=True
    )
    with session_factory() as session:
        assert session.get(User, nuevo_id).is_admin is True


# --- login / logout ---------------------------------------------------------------


def test_login_correcto_devuelve_actor_y_crea_sesion(identity_service, session_factory):
    identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    actor = identity_service.login("ana", CLAVE)
    assert actor.username == "ana"
    assert actor.is_admin is False
    with session_factory() as session:
        sesion = session.get(LoginSession, actor.session_id)
        assert sesion is not None
        assert sesion.ended_at is None
        user = session.scalar(select(User).where(User.username == "ana"))
        assert user.failed_attempts == 0


def test_login_incorrecto_y_usuario_inexistente_dan_el_mismo_mensaje(identity_service):
    identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    with pytest.raises(AuthenticationError) as exc_mala:
        identity_service.login("ana", "mala-clave")
    with pytest.raises(AuthenticationError) as exc_fantasma:
        identity_service.login("fantasma", "lo-que-sea")
    assert str(exc_mala.value) == str(exc_fantasma.value)


def test_usuario_inactivo_da_el_mismo_mensaje_generico(identity_service):
    user_id = identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    identity_service.set_active(SYSTEM_ACTOR, user_id, False)
    with pytest.raises(AuthenticationError) as exc_inactivo:
        identity_service.login("ana", CLAVE)
    with pytest.raises(AuthenticationError) as exc_fantasma:
        identity_service.login("nadie", CLAVE)
    assert str(exc_inactivo.value) == str(exc_fantasma.value)


def test_bloqueo_tras_5_fallos_y_desbloqueo_tras_5_minutos(identity_service, mutable_clock):
    identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    for _ in range(4):
        with pytest.raises(AuthenticationError):
            identity_service.login("ana", "mala")

    with pytest.raises(AuthenticationError) as exc:
        identity_service.login("ana", "mala")
    assert "bloqueada" in str(exc.value).lower()

    # Sigue bloqueada aunque la contraseña ahora sea correcta.
    with pytest.raises(AuthenticationError) as exc_bloqueada:
        identity_service.login("ana", CLAVE)
    assert "bloqueada" in str(exc_bloqueada.value).lower()

    mutable_clock.advance(timedelta(minutes=5, seconds=1))
    actor = identity_service.login("ana", CLAVE)
    assert actor.username == "ana"


def test_auth_failure_persiste_aunque_el_login_falle(identity_service, session_factory):
    identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    with pytest.raises(AuthenticationError):
        identity_service.login("ana", "mala")
    with session_factory() as session:
        fallos = session.query(AuthFailure).all()
        assert len(fallos) == 1
        assert fallos[0].username_intentado == "ana"
        assert fallos[0].occurred_at is not None


def test_logout_cierra_la_sesion(identity_service, session_factory):
    identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    actor = identity_service.login("ana", CLAVE)
    identity_service.logout(actor)
    with session_factory() as session:
        sesion = session.get(LoginSession, actor.session_id)
        assert sesion.ended_at is not None


# --- desactivación / revocación ----------------------------------------------------


def test_desactivar_usuario_hace_fallar_el_siguiente_require(
    identity_service, authorizer, session_factory
):
    user_id = identity_service.create_user(
        SYSTEM_ACTOR, "ana", "Ana", CLAVE, profile_code="vendedor"
    )
    actor = _actor(user_id, "ana")
    with session_factory() as session:
        authorizer.require(session, actor, "core.usuarios.ver")

    identity_service.set_active(SYSTEM_ACTOR, user_id, False)

    with session_factory() as session, pytest.raises(PermissionDenied):
        authorizer.require(session, actor, "core.usuarios.ver")


def test_no_se_puede_desactivar_al_ultimo_admin_activo(identity_service):
    admin_id = identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    with pytest.raises(ValidationError):
        identity_service.set_active(SYSTEM_ACTOR, admin_id, False)


def test_admin_no_puede_desactivarse_a_si_mismo(identity_service):
    admin_id = identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    identity_service.create_user(SYSTEM_ACTOR, "admin2", "Admin Dos", CLAVE, is_admin=True)
    actor_admin1 = _actor(admin_id, "admin1", is_admin=True)
    with pytest.raises(ValidationError):
        identity_service.set_active(actor_admin1, admin_id, False)


# --- contraseñas ---------------------------------------------------------------


def test_change_password_verifica_la_actual_y_permite_login_con_la_nueva(identity_service):
    user_id = identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    actor = _actor(user_id, "ana")
    with pytest.raises(AuthenticationError):
        identity_service.change_password(actor, "mala", "clavenueva1")
    identity_service.change_password(actor, CLAVE, "clavenueva1")
    identity_service.login("ana", "clavenueva1")


def test_reset_password_fuerza_cambio_en_el_proximo_login(identity_service, session_factory):
    user_id = identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    identity_service.reset_password(SYSTEM_ACTOR, user_id, "otraclave1")
    with session_factory() as session:
        assert session.get(User, user_id).must_change_password is True
    identity_service.login("ana", "otraclave1")


# --- listado ---------------------------------------------------------------------


def test_list_users_pagina_y_cuenta_el_total(identity_service):
    for i in range(3):
        identity_service.create_user(SYSTEM_ACTOR, f"user{i}", f"User {i}", CLAVE)
    pagina = identity_service.list_users(SYSTEM_ACTOR, page=1, page_size=2)
    assert pagina.total == 3
    assert len(pagina.items) == 2


# --- auditoría sin secretos --------------------------------------------------------


def test_ningun_evento_de_auditoria_contiene_la_contrasena(identity_service, session_factory):
    user_id = identity_service.create_user(SYSTEM_ACTOR, "ana", "Ana", CLAVE)
    actor = identity_service.login("ana", CLAVE)
    identity_service.change_password(actor, CLAVE, "clavenueva1")
    identity_service.reset_password(SYSTEM_ACTOR, user_id, "otraclave2")

    with session_factory() as session:
        eventos = session.query(AuditEvent).all()
        assert len(eventos) >= 3
        for evento in eventos:
            assert CLAVE not in (evento.summary or "")
            assert "clavenueva1" not in (evento.summary or "")
            assert "otraclave2" not in (evento.summary or "")
            if evento.detail_json:
                assert CLAVE not in evento.detail_json
                assert "clavenueva1" not in evento.detail_json
                assert "otraclave2" not in evento.detail_json
