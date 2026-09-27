"""Pruebas de Authorizer: permisos efectivos, bloqueo/inactividad y códigos no registrados."""

from datetime import UTC, datetime, timedelta

import pytest

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.models import UserPermission
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.errors import PermissionDenied
from sistemashn.core.identity.models import User
from sistemashn.core.modules.contracts import ModuleDef, ModuleRegistry, PermissionDef, ProfileDef

PERMISO_VER = PermissionDef("core.usuarios.ver", "Ver usuarios", "Administración")
PERMISO_GESTIONAR = PermissionDef("core.usuarios.gestionar", "Gestionar usuarios", "Administración")
PERFIL_VENDEDOR = ProfileDef("vendedor", "Vendedor", frozenset({PERMISO_VER.code}))


@pytest.fixture
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(
        ModuleDef(
            code="core",
            label="Core",
            permissions=(PERMISO_VER, PERMISO_GESTIONAR),
            profiles=(PERFIL_VENDEDOR,),
        )
    )
    return reg


@pytest.fixture
def authorizer(registry) -> Authorizer:
    return Authorizer(registry)


def _crear_usuario(
    session_factory,
    now,
    *,
    username: str = "vendedor1",
    is_admin: bool = False,
    is_active: bool = True,
    profile_code: str | None = None,
    locked_until=None,
) -> int:
    with session_factory() as session:
        user = User(
            username=username,
            full_name="Usuario de prueba",
            password_hash="hash",
            is_admin=is_admin,
            is_active=is_active,
            profile_code=profile_code,
            permissions_version=1,
            failed_attempts=0,
            locked_until=locked_until,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        return user.id


def _actor(user_id: int, *, is_admin: bool = False, username: str = "vendedor1") -> Actor:
    return Actor(user_id=user_id, username=username, is_admin=is_admin, session_id="s1")


def test_perfil_mas_override_otorga_y_quita(session_factory, now, authorizer) -> None:
    user_id = _crear_usuario(session_factory, now, profile_code=PERFIL_VENDEDOR.code)
    with session_factory() as session:
        # Override que quita un permiso del perfil.
        session.add(
            UserPermission(user_id=user_id, permission_code=PERMISO_VER.code, granted=False)
        )
        # Override que otorga un permiso fuera del perfil.
        session.add(
            UserPermission(user_id=user_id, permission_code=PERMISO_GESTIONAR.code, granted=True)
        )
        session.commit()

        efectivos = authorizer.effective_permissions(session, user_id)
        assert efectivos == frozenset({PERMISO_GESTIONAR.code})


def test_admin_tiene_todo_incluso_permiso_registrado_despues(
    session_factory, now, registry, authorizer
) -> None:
    user_id = _crear_usuario(session_factory, now, is_admin=True)
    registry.register(
        ModuleDef(
            code="extra",
            label="Extra",
            permissions=(PermissionDef("extra.cosa.hacer", "Hacer cosa", "Extra"),),
        )
    )
    with session_factory() as session:
        efectivos = authorizer.effective_permissions(session, user_id)
        assert "extra.cosa.hacer" in efectivos
        actor = _actor(user_id, is_admin=True)
        authorizer.require(session, actor, "extra.cosa.hacer")


def test_revocar_permiso_con_actor_en_memoria_hace_fallar_el_siguiente_require(
    session_factory, now, authorizer
) -> None:
    user_id = _crear_usuario(session_factory, now, profile_code=PERFIL_VENDEDOR.code)
    actor = _actor(user_id)

    with session_factory() as session:
        authorizer.require(session, actor, PERMISO_VER.code)

    with session_factory() as session:
        session.add(
            UserPermission(user_id=user_id, permission_code=PERMISO_VER.code, granted=False)
        )
        session.commit()

    with session_factory() as session, pytest.raises(PermissionDenied):
        authorizer.require(session, actor, PERMISO_VER.code)


def test_usuario_inactivo_deniega(session_factory, now, authorizer) -> None:
    user_id = _crear_usuario(
        session_factory, now, profile_code=PERFIL_VENDEDOR.code, is_active=False
    )
    actor = _actor(user_id)
    with session_factory() as session, pytest.raises(PermissionDenied):
        authorizer.require(session, actor, PERMISO_VER.code)


def test_usuario_bloqueado_deniega(session_factory, now, authorizer) -> None:
    futuro = datetime.now(UTC) + timedelta(minutes=5)
    user_id = _crear_usuario(
        session_factory, now, profile_code=PERFIL_VENDEDOR.code, locked_until=futuro
    )
    actor = _actor(user_id)
    with session_factory() as session, pytest.raises(PermissionDenied):
        authorizer.require(session, actor, PERMISO_VER.code)


def test_usuario_inexistente_deniega(session_factory, authorizer) -> None:
    actor = _actor(user_id=999, username="fantasma")
    with session_factory() as session, pytest.raises(PermissionDenied):
        authorizer.require(session, actor, PERMISO_VER.code)


def test_codigo_no_registrado_lanza_value_error(session_factory, now, authorizer) -> None:
    user_id = _crear_usuario(session_factory, now, is_admin=True)
    actor = _actor(user_id, is_admin=True)
    with session_factory() as session, pytest.raises(ValueError):
        authorizer.require(session, actor, "no.existe.permiso")


def test_system_actor_tiene_todo(session_factory, authorizer) -> None:
    from sistemashn.core.authorization.actor import SYSTEM_ACTOR

    with session_factory() as session:
        authorizer.require(session, SYSTEM_ACTOR, PERMISO_GESTIONAR.code)
        assert authorizer.can(session, SYSTEM_ACTOR, PERMISO_VER.code) is True
