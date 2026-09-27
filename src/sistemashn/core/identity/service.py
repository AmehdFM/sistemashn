"""Servicio de identidad: alta/edición de usuarios, autenticación y sesiones (T1.2)."""

import functools
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import SYSTEM_ACTOR, Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import (
    AuthenticationError,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from sistemashn.core.identity.models import AuthFailure, LoginSession, User
from sistemashn.core.identity.passwords import hash_password, needs_rehash, verify_password
from sistemashn.core.pagination import Page, normalize_page

_USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,32}$")
_MAX_FAILED_ATTEMPTS = 5
_LOCK_DURATION = timedelta(minutes=5)
_MENSAJE_LOGIN_INVALIDO = "Usuario o contraseña incorrectos"
_MENSAJE_BLOQUEADO = "Cuenta bloqueada temporalmente"

# Sentinel para distinguir "no se pasó profile_code" de "se pasó profile_code=None"
# (quitar el perfil actual) en `update_user`.
_SIN_CAMBIO = object()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_username(username: str) -> str:
    """Minúsculas y sin espacios (recorta extremos); no valida el formato."""
    return username.strip().lower()


def _es_admin_en_bd(session: Session, actor: Actor) -> bool:
    if actor.user_id == SYSTEM_ACTOR.user_id:
        return True
    actor_user = session.get(User, actor.user_id)
    return actor_user is not None and actor_user.is_admin


@dataclass(frozen=True)
class UserView:
    """Proyección de solo lectura de un `User`, sin el hash de contraseña."""

    id: int
    username: str
    full_name: str
    is_admin: bool
    is_active: bool
    profile_code: str | None
    must_change_password: bool
    locked_until: datetime | None = None


def _to_view(user: User) -> UserView:
    return UserView(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        profile_code=user.profile_code,
        must_change_password=user.must_change_password,
        locked_until=user.locked_until,
    )


@functools.cache
def _dummy_hash() -> str:
    return hash_password("contraseña-señuelo-no-usada")


class IdentityService:
    """Alta, edición y autenticación de usuarios del Core."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    def create_user(
        self,
        actor: Actor,
        username: str,
        full_name: str,
        password: str,
        *,
        profile_code: str | None = None,
        is_admin: bool = False,
    ) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "core.usuarios.gestionar")

            normalizado = normalize_username(username)
            if not _USERNAME_RE.match(normalizado):
                raise ValidationError("nombre de usuario inválido: 3-32 caracteres [a-z0-9._-]")
            existente = session.scalar(select(User).where(User.username == normalizado))
            if existente is not None:
                raise ValidationError(f"el usuario '{normalizado}' ya existe")

            if is_admin and not _es_admin_en_bd(session, actor):
                raise PermissionDenied("solo un administrador puede crear otro administrador")

            password_hash = hash_password(password)
            ahora = self.clock()
            user = User(
                username=normalizado,
                full_name=full_name,
                password_hash=password_hash,
                is_admin=is_admin,
                is_active=True,
                profile_code=profile_code,
                permissions_version=1,
                failed_attempts=0,
                locked_until=None,
                must_change_password=False,
                created_at=ahora,
                updated_at=ahora,
            )
            session.add(user)
            session.flush()

            audit(
                session,
                actor,
                "core.usuarios.creado",
                entity_type="core_user",
                entity_id=str(user.id),
                summary=f"Usuario '{normalizado}' creado",
                detail={
                    "username": normalizado,
                    "is_admin": is_admin,
                    "profile_code": profile_code,
                },
                clock=self.clock,
            )
            return user.id

        return run_in_transaction(self.factory, _op)

    def update_user(
        self,
        actor: Actor,
        user_id: int,
        *,
        full_name: str | None = None,
        profile_code=_SIN_CAMBIO,
    ) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "core.usuarios.gestionar")
            user = session.get(User, user_id)
            if user is None:
                raise NotFound(f"usuario {user_id} no existe")

            cambios: dict[str, object] = {}
            if full_name is not None:
                user.full_name = full_name
                cambios["full_name"] = full_name
            if profile_code is not _SIN_CAMBIO:
                user.profile_code = profile_code
                user.permissions_version += 1
                cambios["profile_code"] = profile_code
            user.updated_at = self.clock()
            session.flush()

            audit(
                session,
                actor,
                "core.usuarios.actualizado",
                entity_type="core_user",
                entity_id=str(user_id),
                summary=f"Usuario '{user.username}' actualizado",
                detail=cambios,
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def set_active(self, actor: Actor, user_id: int, active: bool) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "core.usuarios.gestionar")
            user = session.get(User, user_id)
            if user is None:
                raise NotFound(f"usuario {user_id} no existe")

            if not active:
                if user.id == actor.user_id:
                    raise ValidationError("no puede desactivarse a sí mismo")
                if user.is_admin:
                    otros_admins_activos = session.scalar(
                        select(func.count())
                        .select_from(User)
                        .where(
                            User.is_admin.is_(True),
                            User.is_active.is_(True),
                            User.id != user.id,
                        )
                    )
                    if not otros_admins_activos:
                        raise ValidationError("no puede desactivar al último administrador activo")

            user.is_active = active
            user.updated_at = self.clock()
            session.flush()

            audit(
                session,
                actor,
                "core.usuarios.activo_cambiado",
                entity_type="core_user",
                entity_id=str(user_id),
                summary=f"Usuario '{user.username}' {'activado' if active else 'desactivado'}",
                detail={"active": active},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def reset_password(self, actor: Actor, user_id: int, new_password: str) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "core.usuarios.gestionar")
            user = session.get(User, user_id)
            if user is None:
                raise NotFound(f"usuario {user_id} no existe")

            user.password_hash = hash_password(new_password)
            user.must_change_password = True
            user.failed_attempts = 0
            user.locked_until = None
            user.updated_at = self.clock()
            session.flush()

            audit(
                session,
                actor,
                "core.usuarios.contrasena_restablecida",
                entity_type="core_user",
                entity_id=str(user_id),
                summary=f"Contraseña de '{user.username}' restablecida por un administrador",
                detail={"forzado_cambio": True},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def change_password(self, actor: Actor, old_password: str, new_password: str) -> None:
        """El propio usuario cambia su contraseña; verifica `old_password`."""

        def _op(session: Session) -> None:
            user = session.get(User, actor.user_id)
            if user is None:
                raise NotFound("usuario no existe")
            if not verify_password(user.password_hash, old_password):
                raise AuthenticationError("la contraseña actual no es correcta")

            user.password_hash = hash_password(new_password)
            user.must_change_password = False
            user.updated_at = self.clock()
            session.flush()

            audit(
                session,
                actor,
                "core.usuarios.contrasena_cambiada",
                entity_type="core_user",
                entity_id=str(user.id),
                summary=f"'{user.username}' cambió su contraseña",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def list_users(self, actor: Actor, page: int = 1, page_size: int = 50) -> Page[UserView]:
        def _op(session: Session) -> Page[UserView]:
            self.authorizer.require(session, actor, "core.usuarios.ver")
            page_num, size, offset = normalize_page(page, page_size)

            total = session.scalar(select(func.count()).select_from(User)) or 0
            filas = session.scalars(
                select(User).order_by(User.username).offset(offset).limit(size)
            ).all()
            items = [_to_view(u) for u in filas]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def login(self, username: str, password: str) -> Actor:
        """Autentica y devuelve un `Actor`. Mensajes genéricos: no revelan si el usuario existe."""
        normalizado = normalize_username(username)

        def _verificar(session: Session) -> tuple[str, int | None]:
            user = session.scalar(select(User).where(User.username == normalizado))
            ahora = self.clock()
            if user is None:
                # Mismo costo que una verificación real: el tiempo no revela si existe.
                verify_password(_dummy_hash(), password)
                return "no_existe", None
            if user.locked_until is not None and user.locked_until > ahora:
                return "bloqueado", user.id
            if not user.is_active:
                return "inactivo", user.id
            if not verify_password(user.password_hash, password):
                return "password_incorrecta", user.id
            return "ok", user.id

        resultado, user_id = run_in_transaction(self.factory, _verificar, readonly=True)

        if resultado == "ok":

            def _completar(session: Session) -> Actor:
                user = session.get(User, user_id)
                assert user is not None
                user.failed_attempts = 0
                user.locked_until = None
                if needs_rehash(user.password_hash):
                    user.password_hash = hash_password(password)
                ahora = self.clock()
                user.updated_at = ahora

                session_id = str(uuid4())
                session.add(
                    LoginSession(id=session_id, user_id=user.id, started_at=ahora, ended_at=None)
                )
                session.flush()

                actor = Actor(
                    user_id=user.id,
                    username=user.username,
                    is_admin=user.is_admin,
                    session_id=session_id,
                )
                audit(
                    session,
                    actor,
                    "core.sesion.iniciada",
                    entity_type="core_user",
                    entity_id=str(user.id),
                    summary=f"'{user.username}' inició sesión",
                    clock=self.clock,
                )
                return actor

            return run_in_transaction(self.factory, _completar)

        def _registrar_fallo(session: Session) -> bool:
            """Aplica el fallo y devuelve True si esta llamada acaba de bloquear la cuenta."""
            ahora = self.clock()
            recien_bloqueada = False
            if user_id is not None and resultado == "password_incorrecta":
                user = session.get(User, user_id)
                if user is not None:
                    user.failed_attempts += 1
                    if user.failed_attempts >= _MAX_FAILED_ATTEMPTS:
                        user.locked_until = ahora + _LOCK_DURATION
                        recien_bloqueada = True
                    user.updated_at = ahora
            session.add(
                AuthFailure(
                    username_intentado=normalizado[:64],
                    occurred_at=ahora,
                    reason=resultado,
                )
            )
            session.flush()
            return recien_bloqueada

        # Transacción propia: se confirma aunque el login falle.
        recien_bloqueada = run_in_transaction(self.factory, _registrar_fallo)

        if resultado == "bloqueado" or recien_bloqueada:
            raise AuthenticationError(_MENSAJE_BLOQUEADO)
        raise AuthenticationError(_MENSAJE_LOGIN_INVALIDO)

    def logout(self, actor: Actor) -> None:
        def _op(session: Session) -> None:
            sesion = session.get(LoginSession, actor.session_id)
            if sesion is not None and sesion.ended_at is None:
                sesion.ended_at = self.clock()
                session.flush()

        run_in_transaction(self.factory, _op)
