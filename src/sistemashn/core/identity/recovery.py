"""Recuperación de acceso: códigos de un solo uso y autorización asistida del vendedor (T1.2)."""

import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import SYSTEM_ACTOR, Actor
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import AuthenticationError, NotFound, PermissionDenied
from sistemashn.core.identity.models import RecoveryChallenge, RecoveryCode, User
from sistemashn.core.identity.passwords import hash_password
from sistemashn.core.licensing.codec import CodecError, verify_signed

_ALFABETO_SIN_AMBIGUOS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_VENDOR_TOKEN_PREFIX = "SHNREC1"
_VENDOR_TOKEN_TTL = timedelta(hours=72)
_MENSAJE_CODIGO_INVALIDO = "Código de recuperación inválido o ya usado"
_MENSAJE_TOKEN_INVALIDO = "Autorización de vendedor inválida"
_MENSAJE_TOKEN_VENCIDO = "Autorización de vendedor vencida"

_code_hasher = PasswordHasher()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _generar_codigo() -> str:
    grupos = ["".join(secrets.choice(_ALFABETO_SIN_AMBIGUOS) for _ in range(4)) for _ in range(3)]
    return "-".join(grupos)


def _verificar_codigo(code_hash: str, code: str) -> bool:
    try:
        return _code_hasher.verify(code_hash, code)
    except VerifyMismatchError, VerificationError, InvalidHash:
        return False


def _admin_activo_mas_antiguo(session: Session) -> User | None:
    return session.scalar(
        select(User)
        .where(User.is_admin.is_(True), User.is_active.is_(True))
        .order_by(User.created_at.asc(), User.id.asc())
    )


def generate_codes(
    session: Session,
    n: int = 8,
    *,
    clock: Callable[[], datetime] = _utcnow,
) -> list[str]:
    """Genera `n` códigos de recuperación nuevos e invalida los anteriores no usados.

    Pensada para llamarse dentro de una transacción ya abierta por otro servicio (p. ej.
    el asistente de primer arranque, que crea el admin y sus códigos en la misma sesión).
    Solo se guardan los hashes argon2 de los códigos; el texto en claro se devuelve una vez.
    """
    ahora = clock()

    pendientes = session.scalars(select(RecoveryCode).where(RecoveryCode.used_at.is_(None))).all()
    for anterior in pendientes:
        anterior.used_at = ahora

    codigos: list[str] = []
    vistos: set[str] = set()
    while len(codigos) < n:
        codigo = _generar_codigo()
        if codigo in vistos:
            continue
        vistos.add(codigo)
        codigos.append(codigo)
        session.add(
            RecoveryCode(
                code_hash=_code_hasher.hash(codigo),
                created_at=ahora,
                used_at=None,
                used_by_user_id=None,
            )
        )
    session.flush()
    return codigos


class RecoveryService:
    """Recuperación del admin: códigos locales o autorización firmada por el vendedor."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        clock: Callable[[], datetime],
        public_keys: dict[str, bytes],
        installation_id_fn: Callable[[], str],
    ) -> None:
        self.factory = factory
        self.clock = clock
        self.public_keys = public_keys
        self.installation_id_fn = installation_id_fn

    def regenerate_codes(self, actor: Actor, n: int = 8) -> list[str]:
        def _op(session: Session) -> list[str]:
            actor_es_admin = actor.user_id == SYSTEM_ACTOR.user_id or (
                (actor_user := session.get(User, actor.user_id)) is not None and actor_user.is_admin
            )
            if not actor_es_admin:
                raise PermissionDenied(
                    "solo un administrador puede regenerar códigos de recuperación"
                )

            codigos = generate_codes(session, n, clock=self.clock)
            audit(
                session,
                actor,
                "core.recuperacion.codigos_regenerados",
                summary="Códigos de recuperación regenerados",
                detail={"cantidad": len(codigos)},
                clock=self.clock,
            )
            return codigos

        return run_in_transaction(self.factory, _op)

    def recover_with_code(self, code: str, new_password: str) -> None:
        def _op(session: Session) -> None:
            candidatos = session.scalars(
                select(RecoveryCode).where(RecoveryCode.used_at.is_(None))
            ).all()
            encontrado = next((c for c in candidatos if _verificar_codigo(c.code_hash, code)), None)
            if encontrado is None:
                raise AuthenticationError(_MENSAJE_CODIGO_INVALIDO)

            admin = _admin_activo_mas_antiguo(session)
            if admin is None:
                raise NotFound("no hay administrador activo")

            ahora = self.clock()
            admin.password_hash = hash_password(new_password)
            admin.must_change_password = True
            admin.failed_attempts = 0
            admin.locked_until = None
            admin.updated_at = ahora

            encontrado.used_at = ahora
            encontrado.used_by_user_id = admin.id
            session.flush()

            audit(
                session,
                SYSTEM_ACTOR,
                "core.recuperacion.codigo",
                entity_type="core_user",
                entity_id=str(admin.id),
                summary=f"Recuperación de '{admin.username}' con código de recuperación",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def create_challenge(self) -> str:
        def _op(session: Session) -> str:
            nonce = secrets.token_urlsafe(16)
            session.add(RecoveryChallenge(nonce=nonce, issued_at=self.clock(), used_at=None))
            session.flush()
            return nonce

        nonce = run_in_transaction(self.factory, _op)
        return f"SHNCHL1.{self.installation_id_fn()}.{nonce}"

    def recover_with_vendor_token(self, token: str, new_password: str) -> None:
        try:
            payload = verify_signed(token, _VENDOR_TOKEN_PREFIX, self.public_keys)
        except CodecError as exc:
            raise AuthenticationError(_MENSAJE_TOKEN_INVALIDO) from exc

        if payload.get("action") != "reset_admin":
            raise AuthenticationError(_MENSAJE_TOKEN_INVALIDO)
        if payload.get("installation_id") != self.installation_id_fn():
            raise AuthenticationError(_MENSAJE_TOKEN_INVALIDO)
        nonce = payload.get("challenge_nonce")
        if not isinstance(nonce, str):
            raise AuthenticationError(_MENSAJE_TOKEN_INVALIDO)

        def _op(session: Session) -> None:
            challenge = session.scalar(
                select(RecoveryChallenge).where(RecoveryChallenge.nonce == nonce)
            )
            if challenge is None or challenge.used_at is not None:
                raise AuthenticationError(_MENSAJE_TOKEN_INVALIDO)

            ahora = self.clock()
            if ahora - challenge.issued_at >= _VENDOR_TOKEN_TTL:
                raise AuthenticationError(_MENSAJE_TOKEN_VENCIDO)

            admin = _admin_activo_mas_antiguo(session)
            if admin is None:
                raise NotFound("no hay administrador activo")

            admin.password_hash = hash_password(new_password)
            admin.must_change_password = True
            admin.failed_attempts = 0
            admin.locked_until = None
            admin.updated_at = ahora

            challenge.used_at = ahora
            session.flush()

            audit(
                session,
                SYSTEM_ACTOR,
                "core.recuperacion.vendedor",
                entity_type="core_user",
                entity_id=str(admin.id),
                summary=f"Recuperación de '{admin.username}' con autorización de vendedor",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)
