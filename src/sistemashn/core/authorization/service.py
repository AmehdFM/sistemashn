"""Autorización: permisos efectivos de un usuario y administración de overrides (plan T1.1)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import SYSTEM_ACTOR, Actor
from sistemashn.core.authorization.models import UserPermission
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, PermissionDenied, ValidationError
from sistemashn.core.identity.models import User
from sistemashn.core.modules.contracts import ModuleRegistry


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Authorizer:
    """Calcula y verifica permisos efectivos a partir del registro de módulos."""

    def __init__(self, registry: ModuleRegistry, clock: Callable[[], datetime] = _utcnow) -> None:
        self.registry = registry
        self.clock = clock

    def effective_permissions(self, session: Session, user_id: int) -> frozenset[str]:
        if user_id == SYSTEM_ACTOR.user_id:
            return frozenset(self.registry.permissions().keys())

        user = session.get(User, user_id)
        if user is None:
            return frozenset()
        if user.is_admin:
            return frozenset(self.registry.permissions().keys())

        permisos: set[str] = set()
        if user.profile_code:
            perfil = self.registry.profiles().get(user.profile_code)
            if perfil is not None:
                permisos |= set(perfil.permissions)

        overrides = session.query(UserPermission).filter(UserPermission.user_id == user.id).all()
        for override in overrides:
            if override.granted:
                permisos.add(override.permission_code)
            else:
                permisos.discard(override.permission_code)
        return frozenset(permisos)

    def can(self, session: Session, actor: Actor, code: str) -> bool:
        if code not in self.registry.permissions():
            raise ValueError(f"permiso no registrado: {code}")

        if actor.user_id == SYSTEM_ACTOR.user_id:
            return True

        user = session.get(User, actor.user_id)
        if user is None or not user.is_active:
            return False
        if user.locked_until is not None and user.locked_until > self.clock():
            return False

        return code in self.effective_permissions(session, actor.user_id)

    def require(self, session: Session, actor: Actor, code: str) -> None:
        if not self.can(session, actor, code):
            raise PermissionDenied(f"'{actor.username}' no tiene el permiso '{code}'")


class PermissionAdminService:
    """Gestiona el perfil y los overrides de permisos de un usuario."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime],
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    def set_user_permissions(
        self,
        actor: Actor,
        user_id: int,
        profile_code: str | None,
        overrides: dict[str, bool],
    ) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "core.usuarios.gestionar")

            target = session.get(User, user_id)
            if target is None:
                raise NotFound(f"usuario {user_id} no existe")

            permisos_registrados = self.authorizer.registry.permissions()
            perfiles_registrados = self.authorizer.registry.profiles()

            if profile_code is not None and profile_code not in perfiles_registrados:
                raise ValidationError(f"perfil inexistente: {profile_code}")
            for code in overrides:
                if code not in permisos_registrados:
                    raise ValidationError(f"permiso inexistente: {code}")

            # El rol de admin se lee de la base, no del Actor en memoria (puede estar revocado).
            actor_user = session.get(User, actor.user_id)
            actor_es_admin = actor.user_id == SYSTEM_ACTOR.user_id or (
                actor_user is not None and actor_user.is_admin
            )
            if not actor_es_admin and target.is_admin:
                raise PermissionDenied("un no-administrador no puede modificar a un admin")

            antes = self.authorizer.effective_permissions(session, user_id)

            session.query(UserPermission).filter(UserPermission.user_id == user_id).delete()
            for code, granted in overrides.items():
                session.add(UserPermission(user_id=user_id, permission_code=code, granted=granted))
            target.profile_code = profile_code
            target.permissions_version += 1
            target.updated_at = self.clock()
            session.flush()

            despues = self.authorizer.effective_permissions(session, user_id)
            if not actor_es_admin:
                # Ni por override ni por perfil puede otorgar algo que él mismo no tiene.
                permisos_actor = self.authorizer.effective_permissions(session, actor.user_id)
                ganados = despues - antes - permisos_actor
                if ganados:
                    raise PermissionDenied(
                        "no puede otorgar permisos que no posee: " + ", ".join(sorted(ganados))
                    )
            audit(
                session,
                actor,
                "core.usuarios.permisos_cambiados",
                entity_type="core_user",
                entity_id=str(user_id),
                summary=f"Permisos de '{target.username}' modificados",
                detail={
                    "perfil": profile_code,
                    "overrides": overrides,
                    "antes": sorted(antes),
                    "despues": sorted(despues),
                },
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)
