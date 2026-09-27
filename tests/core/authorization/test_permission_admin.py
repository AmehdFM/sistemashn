"""Pruebas de PermissionAdminService: reemplazo de overrides, escalado y version."""

import pytest

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.models import UserPermission
from sistemashn.core.authorization.service import Authorizer, PermissionAdminService
from sistemashn.core.errors import PermissionDenied, ValidationError
from sistemashn.core.identity.models import User
from sistemashn.core.modules.contracts import ModuleDef, ModuleRegistry, PermissionDef, ProfileDef

PERMISO_VER = PermissionDef("core.usuarios.ver", "Ver usuarios", "Administración")
PERMISO_GESTIONAR = PermissionDef("core.usuarios.gestionar", "Gestionar usuarios", "Administración")
PERMISO_AUDITORIA = PermissionDef("core.auditoria.ver", "Ver auditoría", "Administración")
PERFIL_VENDEDOR = ProfileDef("vendedor", "Vendedor", frozenset({PERMISO_VER.code}))


@pytest.fixture
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(
        ModuleDef(
            code="core",
            label="Core",
            permissions=(PERMISO_VER, PERMISO_GESTIONAR, PERMISO_AUDITORIA),
            profiles=(PERFIL_VENDEDOR,),
        )
    )
    return reg


@pytest.fixture
def authorizer(registry) -> Authorizer:
    return Authorizer(registry)


@pytest.fixture
def service(session_factory, authorizer, clock) -> PermissionAdminService:
    return PermissionAdminService(session_factory, authorizer, clock)


def _crear_usuario(
    session_factory,
    now,
    *,
    username: str,
    is_admin: bool = False,
    profile_code: str | None = None,
) -> int:
    with session_factory() as session:
        user = User(
            username=username,
            full_name=username,
            password_hash="hash",
            is_admin=is_admin,
            is_active=True,
            profile_code=profile_code,
            permissions_version=1,
            failed_attempts=0,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        return user.id


def _actor(user_id: int, *, is_admin: bool = False, username: str = "actor") -> Actor:
    return Actor(user_id=user_id, username=username, is_admin=is_admin, session_id="s1")


def test_set_permissions_reemplaza_overrides_y_sube_version(
    session_factory, now, service, authorizer
) -> None:
    admin_id = _crear_usuario(session_factory, now, username="admin", is_admin=True)
    target_id = _crear_usuario(session_factory, now, username="vendedor1")
    admin = _actor(admin_id, is_admin=True, username="admin")

    service.set_user_permissions(
        admin, target_id, PERFIL_VENDEDOR.code, {PERMISO_GESTIONAR.code: True}
    )

    with session_factory() as session:
        target = session.get(User, target_id)
        assert target.profile_code == PERFIL_VENDEDOR.code
        assert target.permissions_version == 2
        efectivos = authorizer.effective_permissions(session, target_id)
        assert efectivos == frozenset({PERMISO_VER.code, PERMISO_GESTIONAR.code})

    # Reemplaza (no acumula): un segundo set sin ese override lo quita.
    service.set_user_permissions(admin, target_id, PERFIL_VENDEDOR.code, {})
    with session_factory() as session:
        target = session.get(User, target_id)
        assert target.permissions_version == 3
        overrides = session.query(UserPermission).filter_by(user_id=target_id).all()
        assert overrides == []


def test_requiere_permiso_core_usuarios_gestionar(session_factory, now, service) -> None:
    sin_permiso_id = _crear_usuario(session_factory, now, username="sinpermiso")
    target_id = _crear_usuario(session_factory, now, username="vendedor1")
    actor = _actor(sin_permiso_id, username="sinpermiso")

    with pytest.raises(PermissionDenied):
        service.set_user_permissions(actor, target_id, None, {})


def test_perfil_inexistente_falla(session_factory, now, service) -> None:
    admin_id = _crear_usuario(session_factory, now, username="admin", is_admin=True)
    target_id = _crear_usuario(session_factory, now, username="vendedor1")
    admin = _actor(admin_id, is_admin=True, username="admin")

    with pytest.raises(ValidationError):
        service.set_user_permissions(admin, target_id, "perfil-fantasma", {})


def test_permiso_inexistente_falla(session_factory, now, service) -> None:
    admin_id = _crear_usuario(session_factory, now, username="admin", is_admin=True)
    target_id = _crear_usuario(session_factory, now, username="vendedor1")
    admin = _actor(admin_id, is_admin=True, username="admin")

    with pytest.raises(ValidationError):
        service.set_user_permissions(admin, target_id, None, {"permiso.fantasma": True})


def test_no_admin_no_escala_privilegios(session_factory, now, service) -> None:
    gestor_id = _crear_usuario(
        session_factory, now, username="gestor", profile_code=PERFIL_VENDEDOR.code
    )
    # El gestor tiene core.usuarios.ver (vía perfil) más el override que le da gestionar.
    with session_factory() as session:
        session.add(
            UserPermission(user_id=gestor_id, permission_code=PERMISO_GESTIONAR.code, granted=True)
        )
        session.commit()

    target_id = _crear_usuario(session_factory, now, username="vendedor2")
    gestor = _actor(gestor_id, username="gestor")

    with pytest.raises(PermissionDenied):
        service.set_user_permissions(gestor, target_id, None, {PERMISO_AUDITORIA.code: True})


def test_no_admin_no_modifica_a_un_admin(session_factory, now, service) -> None:
    gestor_id = _crear_usuario(session_factory, now, username="gestor")
    with session_factory() as session:
        session.add(
            UserPermission(user_id=gestor_id, permission_code=PERMISO_GESTIONAR.code, granted=True)
        )
        session.commit()

    admin_objetivo_id = _crear_usuario(session_factory, now, username="admin2", is_admin=True)
    gestor = _actor(gestor_id, username="gestor")

    with pytest.raises(PermissionDenied):
        service.set_user_permissions(gestor, admin_objetivo_id, None, {})


def test_no_admin_no_escala_por_perfil(session_factory, now, clock) -> None:
    """Asignar un perfil con permisos que el actor no tiene también es escalada."""
    reg = ModuleRegistry()
    reg.register(
        ModuleDef(
            code="core",
            label="Core",
            permissions=(PERMISO_VER, PERMISO_GESTIONAR, PERMISO_AUDITORIA),
            profiles=(ProfileDef("auditor", "Auditor", frozenset({PERMISO_AUDITORIA.code})),),
        )
    )
    service = PermissionAdminService(session_factory, Authorizer(reg, clock), clock)
    gestor_id = _crear_usuario(session_factory, now, username="gestor")
    victima_id = _crear_usuario(session_factory, now, username="otro")
    with session_factory() as session:
        session.add(
            UserPermission(user_id=gestor_id, permission_code=PERMISO_GESTIONAR.code, granted=True)
        )
        session.commit()
    with pytest.raises(PermissionDenied):
        service.set_user_permissions(_actor(gestor_id), victima_id, "auditor", {})


def test_admin_revocado_en_sesion_no_toca_admins(session_factory, now, service) -> None:
    """El rol admin se toma de la base, no del Actor en memoria."""
    ex_admin_id = _crear_usuario(session_factory, now, username="exadmin")
    admin_id = _crear_usuario(session_factory, now, username="admin", is_admin=True)
    with session_factory() as session:
        session.add(
            UserPermission(
                user_id=ex_admin_id, permission_code=PERMISO_GESTIONAR.code, granted=True
            )
        )
        session.commit()
    with pytest.raises(PermissionDenied):
        service.set_user_permissions(_actor(ex_admin_id, is_admin=True), admin_id, None, {})
