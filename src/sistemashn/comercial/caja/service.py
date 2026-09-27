"""Servicio de caja: apertura/cierre de turno y movimientos (plan T4.3)."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.caja.errors import CashSessionAlreadyOpen, NoCashSessionOpen
from sistemashn.comercial.caja.models import CashMovement, CashSession
from sistemashn.comercial.caja.schemas import CashMovementView, CashSessionView
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.money import ZERO, money
from sistemashn.core.pagination import Page, normalize_page

_MOTIVO_MIN_LEN = 5

# Signo de cada tipo de movimiento al calcular el efectivo esperado.
_SIGNO = {"entrada": 1, "venta": 1, "abono": 1, "salida": -1}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CashService:
    """Apertura, cierre, movimientos y consultas de caja."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    # -- Apertura / cierre ---------------------------------------------------

    def open(self, actor: Actor, opening_amount: Decimal) -> CashSessionView:
        def _op(session: Session) -> CashSessionView:
            self.authorizer.require(session, actor, "com.caja.operar")

            if self._abierta(session) is not None:
                raise CashSessionAlreadyOpen("ya hay una sesión de caja abierta")

            monto = money(opening_amount)
            if monto < 0:
                raise ValidationError("el monto de apertura no puede ser negativo")

            ahora = self.clock()
            cash_session = CashSession(
                opened_at=ahora,
                closed_at=None,
                opened_by=actor.user_id,
                closed_by=None,
                opening_amount=monto,
                expected_cash=None,
                counted_cash=None,
                difference=None,
                status="abierta",
                notes=None,
            )
            session.add(cash_session)
            session.flush()

            audit(
                session,
                actor,
                "com.caja.abierta",
                entity_type="com_cash_session",
                entity_id=str(cash_session.id),
                summary=f"Caja abierta con {monto}",
                detail={"opening_amount": monto},
                clock=self.clock,
            )
            return self._to_view(cash_session)

        return run_in_transaction(self.factory, _op)

    def current(self, actor: Actor) -> CashSessionView | None:
        def _op(session: Session) -> CashSessionView | None:
            self.authorizer.require(session, actor, "com.caja.ver")
            cash_session = self._abierta(session)
            return self._to_view(cash_session) if cash_session is not None else None

        return run_in_transaction(self.factory, _op, readonly=True)

    def close(self, actor: Actor, counted_cash: Decimal) -> CashSessionView:
        def _op(session: Session) -> CashSessionView:
            self.authorizer.require(session, actor, "com.caja.cerrar")

            cash_session = self._abierta(session)
            if cash_session is None:
                raise NoCashSessionOpen("no hay una sesión de caja abierta")

            movimientos = session.scalars(
                select(CashMovement).where(CashMovement.cash_session_id == cash_session.id)
            ).all()
            total_movimientos = sum((_SIGNO[m.kind] * m.amount for m in movimientos), ZERO)
            esperado = money(cash_session.opening_amount + total_movimientos)
            contado = money(counted_cash)
            diferencia = money(contado - esperado)

            cash_session.expected_cash = esperado
            cash_session.counted_cash = contado
            cash_session.difference = diferencia
            cash_session.closed_at = self.clock()
            cash_session.closed_by = actor.user_id
            cash_session.status = "cerrada"
            session.flush()

            audit(
                session,
                actor,
                "com.caja.cerrada",
                entity_type="com_cash_session",
                entity_id=str(cash_session.id),
                summary=f"Caja cerrada: esperado {esperado}, contado {contado}",
                detail={
                    "expected_cash": esperado,
                    "counted_cash": contado,
                    "difference": diferencia,
                },
                clock=self.clock,
            )
            return self._to_view(cash_session)

        return run_in_transaction(self.factory, _op)

    # -- Movimientos ---------------------------------------------------------

    def register_entry(
        self,
        session: Session,
        actor: Actor,
        cash_session_id: int,
        amount: Decimal,
        kind: str,
        *,
        reason: str | None = None,
        ref_type: str | None = None,
        ref_id: str | None = None,
    ) -> None:
        """Registra un movimiento de caja dentro de la transacción del documento que lo origina.

        Uso interno (venta/abono en efectivo): no verifica permisos ni abre transacción propia.
        """
        monto = money(amount)
        if monto <= 0:
            raise ValidationError("el monto del movimiento debe ser mayor a cero")

        cash_session = session.get(CashSession, cash_session_id)
        if cash_session is None:
            raise NotFound(f"sesión de caja {cash_session_id} no existe")
        if cash_session.status != "abierta":
            raise NoCashSessionOpen(f"la sesión de caja {cash_session_id} no está abierta")

        session.add(
            CashMovement(
                cash_session_id=cash_session_id,
                occurred_at=self.clock(),
                kind=kind,
                amount=monto,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
                user_id=actor.user_id,
            )
        )
        session.flush()

    def reverse_entry(
        self,
        session: Session,
        actor: Actor,
        cash_session_id: int,
        amount: Decimal,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
    ) -> None:
        """Revierte un cobro en efectivo (p. ej. anular una venta) con un movimiento de salida.

        Uso interno: no verifica permisos ni abre transacción propia. Si la sesión de caja
        donde se cobró ya no existe abierta (se cerró después de la venta), no revierte nada
        silenciosamente: propaga `NoCashSessionOpen` para que el servicio llamador rechace la
        anulación con un mensaje claro.
        """
        monto = money(amount)
        if monto <= 0:
            raise ValidationError("el monto del movimiento debe ser mayor a cero")

        cash_session = session.get(CashSession, cash_session_id)
        if cash_session is None:
            raise NotFound(f"sesión de caja {cash_session_id} no existe")
        if cash_session.status != "abierta":
            raise NoCashSessionOpen(
                f"la sesión de caja {cash_session_id} ya no está abierta: no se puede revertir "
                "el movimiento de efectivo"
            )

        session.add(
            CashMovement(
                cash_session_id=cash_session_id,
                occurred_at=self.clock(),
                kind="salida",
                amount=monto,
                reason=None,
                ref_type=ref_type,
                ref_id=ref_id,
                user_id=actor.user_id,
            )
        )
        session.flush()

    def manual_entry(self, actor: Actor, amount: Decimal, reason: str) -> CashMovementView:
        return self._manual_movement(actor, amount, reason, "entrada")

    def manual_exit(self, actor: Actor, amount: Decimal, reason: str) -> CashMovementView:
        return self._manual_movement(actor, amount, reason, "salida")

    def _manual_movement(
        self, actor: Actor, amount: Decimal, reason: str, kind: str
    ) -> CashMovementView:
        def _op(session: Session) -> CashMovementView:
            self.authorizer.require(session, actor, "com.caja.operar")

            motivo = (reason or "").strip()
            if len(motivo) < _MOTIVO_MIN_LEN:
                raise ValidationError(f"el motivo debe tener al menos {_MOTIVO_MIN_LEN} caracteres")

            cash_session = self._abierta(session)
            if cash_session is None:
                raise NoCashSessionOpen("no hay una sesión de caja abierta")

            monto = money(amount)
            if monto <= 0:
                raise ValidationError("el monto debe ser mayor a cero")

            movimiento = CashMovement(
                cash_session_id=cash_session.id,
                occurred_at=self.clock(),
                kind=kind,
                amount=monto,
                reason=motivo,
                ref_type=None,
                ref_id=None,
                user_id=actor.user_id,
            )
            session.add(movimiento)
            session.flush()

            audit(
                session,
                actor,
                f"com.caja.{kind}",
                entity_type="com_cash_movement",
                entity_id=str(movimiento.id),
                summary=f"{kind.capitalize()} manual de {monto}: {motivo}",
                detail={"amount": monto, "reason": motivo},
                clock=self.clock,
            )
            return self._to_movement_view(movimiento)

        return run_in_transaction(self.factory, _op)

    def movements(
        self,
        actor: Actor,
        cash_session_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> Page[CashMovementView]:
        def _op(session: Session) -> Page[CashMovementView]:
            self.authorizer.require(session, actor, "com.caja.ver")
            page_num, size, offset = normalize_page(page, page_size)

            stmt = select(CashMovement).where(CashMovement.cash_session_id == cash_session_id)
            filas = session.scalars(stmt).all()
            filas_ordenadas = sorted(filas, key=lambda m: (m.occurred_at, m.id), reverse=True)

            total = len(filas_ordenadas)
            pagina = filas_ordenadas[offset : offset + size]
            items = [self._to_movement_view(m) for m in pagina]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def list_sessions(
        self, actor: Actor, page: int = 1, page_size: int = 50
    ) -> Page[CashSessionView]:
        def _op(session: Session) -> Page[CashSessionView]:
            self.authorizer.require(session, actor, "com.caja.ver")
            page_num, size, offset = normalize_page(page, page_size)

            filas = session.scalars(
                select(CashSession).order_by(CashSession.opened_at.desc(), CashSession.id.desc())
            ).all()
            total = len(filas)
            pagina = filas[offset : offset + size]
            items = [self._to_view(f) for f in pagina]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos --------------------------------------------------------

    def _abierta(self, session: Session) -> CashSession | None:
        return session.scalars(
            select(CashSession).where(CashSession.status == "abierta")
        ).one_or_none()

    def _to_view(self, cash_session: CashSession) -> CashSessionView:
        return CashSessionView(
            id=cash_session.id,
            opened_at=cash_session.opened_at,
            closed_at=cash_session.closed_at,
            opened_by=cash_session.opened_by,
            closed_by=cash_session.closed_by,
            opening_amount=cash_session.opening_amount,
            expected_cash=cash_session.expected_cash,
            counted_cash=cash_session.counted_cash,
            difference=cash_session.difference,
            status=cash_session.status,
            notes=cash_session.notes,
        )

    def _to_movement_view(self, movimiento: CashMovement) -> CashMovementView:
        return CashMovementView(
            id=movimiento.id,
            occurred_at=movimiento.occurred_at,
            kind=movimiento.kind,
            amount=movimiento.amount,
            reason=movimiento.reason,
            ref_type=movimiento.ref_type,
            ref_id=movimiento.ref_id,
            user_id=movimiento.user_id,
        )
