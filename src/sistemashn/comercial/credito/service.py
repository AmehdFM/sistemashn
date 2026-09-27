"""Servicio de cuentas por pagar/cobrar: alta interna, abonos y consultas (plan T3.3)."""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.search import normalize_search
from sistemashn.comercial.contrapartes.models import Party
from sistemashn.comercial.credito.errors import OverpaymentError, RequestIdReused
from sistemashn.comercial.credito.models import Account, AccountPayment
from sistemashn.comercial.credito.schemas import (
    AccountKind,
    AccountPaymentView,
    AccountStatus,
    AccountSummary,
    AccountView,
)
from sistemashn.comercial.idempotency import find_previous, remember
from sistemashn.comercial.pagos.methods import PaymentInput
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.text import LIKE_ESCAPE, escape_like
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.money import money
from sistemashn.core.pagination import Page, normalize_page

_OPERATION = "cuenta.pago"

# Honduras no observa horario de verano: UTC-6 todo el año.
_HONDURAS_OFFSET = timedelta(hours=-6)

_VIEW_PERMISSION = {
    AccountKind.PAYABLE: "com.cxp.ver",
    AccountKind.RECEIVABLE: "com.cxc.ver",
    # Una nota de crédito (saldo a favor) se gestiona con el mismo permiso que las devoluciones
    # que la originan: no amerita un permiso de "ver"/"pagar" propio.
    AccountKind.CREDIT_NOTE: "com.devoluciones.gestionar",
}
_PAY_PERMISSION = {
    AccountKind.PAYABLE: "com.cxp.pagar",
    AccountKind.RECEIVABLE: "com.cxc.cobrar",
    AccountKind.CREDIT_NOTE: "com.devoluciones.gestionar",
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AccountService:
    """Alta interna, abonos y consultas de cuentas por pagar/cobrar."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    def _today_honduras(self) -> date:
        return (self.clock() + _HONDURAS_OFFSET).date()

    def _status(self, account: Account) -> tuple[AccountStatus, int]:
        if account.balance == 0:
            return AccountStatus.PAGADA, 0
        hoy = self._today_honduras()
        if hoy > account.due_date:
            return AccountStatus.VENCIDA, (hoy - account.due_date).days
        return AccountStatus.PENDIENTE, 0

    def _to_summary(self, account: Account, party_name: str) -> AccountSummary:
        estado, atraso = self._status(account)
        return AccountSummary(
            id=account.id,
            kind=AccountKind(account.kind),
            party_id=account.party_id,
            party_name=party_name,
            source_type=account.source_type,
            source_id=account.source_id,
            original_amount=account.original_amount,
            balance=account.balance,
            due_date=account.due_date,
            status=estado,
            days_overdue=atraso,
        )

    def _to_view(self, session: Session, account: Account) -> AccountView:
        party = session.get(Party, account.party_id)
        party_name = party.name if party is not None else ""
        resumen = self._to_summary(account, party_name)
        pagos = session.scalars(
            select(AccountPayment)
            .where(AccountPayment.account_id == account.id)
            .order_by(AccountPayment.id.asc())
        ).all()
        payments = tuple(
            AccountPaymentView(
                id=p.id,
                paid_at=p.paid_at,
                method=p.method,
                amount=p.amount,
                reference=p.reference,
                user_id=p.user_id,
            )
            for p in pagos
        )
        return AccountView(
            **resumen.__dict__,
            created_at=account.created_at,
            payments=payments,
        )

    def create_account(
        self,
        session: Session,
        actor: Actor,
        *,
        kind: AccountKind | str,
        party_id: int,
        source_type: str,
        source_id: str,
        amount: Decimal,
        due_date: date,
    ) -> int:
        """Crea una cuenta dentro de la transacción del documento que la origina.

        Uso interno: no verifica permisos (el permiso lo exige el servicio del documento, p.
        ej. `com.compras.registrar`); solo valida los datos y audita el alta.
        """
        account_kind = AccountKind(kind)
        monto = money(amount)
        if monto <= 0:
            raise ValidationError("el monto de la cuenta debe ser mayor a cero")

        party = session.get(Party, party_id)
        if party is None:
            raise NotFound(f"contraparte {party_id} no existe")
        if not party.active:
            raise ValidationError(f"la contraparte '{party.name}' está inactiva")

        cuenta = Account(
            kind=account_kind.value,
            party_id=party_id,
            source_type=source_type,
            source_id=source_id,
            original_amount=monto,
            balance=monto,
            due_date=due_date,
            created_at=self.clock(),
            user_id=actor.user_id,
        )
        session.add(cuenta)
        session.flush()

        audit(
            session,
            actor,
            "com.cuenta.creada",
            entity_type="com_account",
            entity_id=str(cuenta.id),
            summary=f"Cuenta {account_kind.value} #{cuenta.id} por {monto} ({source_type})",
            detail={
                "kind": account_kind.value,
                "party_id": party_id,
                "source_type": source_type,
                "source_id": source_id,
                "amount": monto,
                "due_date": due_date,
            },
            clock=self.clock,
        )
        return cuenta.id

    def void(self, session: Session, actor: Actor, account_id: int) -> None:
        """Salda a cero una cuenta por la anulación del documento que la originó.

        Uso interno: recibe la `session` de la transacción del documento que anula (venta o
        compra), no abre transacción propia ni verifica permiso (el permiso lo exige el
        servicio llamador). No es un abono real: no crea `AccountPayment`.

        Limitación aceptada explícitamente (plan T5.1): `AccountStatus` sigue mostrando
        "pagada" para una cuenta anulada, el mismo criterio que una cuenta saldada normalmente
        (`balance == 0`); no se migra el esquema para agregar un estado "anulada" distinto.
        """
        cuenta = session.get(Account, account_id)
        if cuenta is None:
            raise NotFound(f"cuenta {account_id} no existe")

        saldo_previo = cuenta.balance
        cuenta.balance = money(Decimal("0"))
        session.flush()

        audit(
            session,
            actor,
            "com.cuenta.anulada",
            entity_type="com_account",
            entity_id=str(account_id),
            summary=f"Cuenta #{account_id} anulada (saldo previo {saldo_previo})",
            detail={"balance_before": saldo_previo},
            clock=self.clock,
        )

    def pay(
        self,
        actor: Actor,
        account_id: int,
        payment: PaymentInput,
        request_id: str,
    ) -> AccountView:
        def _op(session: Session) -> AccountView:
            cuenta = session.get(Account, account_id)
            if cuenta is None:
                raise NotFound(f"cuenta {account_id} no existe")
            account_kind = AccountKind(cuenta.kind)
            self.authorizer.require(session, actor, _PAY_PERMISSION[account_kind])

            previo = find_previous(session, request_id, _OPERATION)
            if previo is not None:
                if previo != str(account_id):
                    raise RequestIdReused(
                        f"request_id '{request_id}' ya se usó para abonar la cuenta {previo}"
                    )
                return self._to_view(session, cuenta)

            if payment.amount > cuenta.balance:
                raise OverpaymentError(
                    f"el abono {payment.amount} excede el saldo {cuenta.balance}"
                )

            abono = AccountPayment(
                account_id=account_id,
                paid_at=self.clock(),
                method=payment.method.value,
                amount=payment.amount,
                reference=payment.reference,
                user_id=actor.user_id,
                request_id=request_id,
            )
            session.add(abono)
            cuenta.balance = money(cuenta.balance - payment.amount)
            session.flush()

            remember(session, request_id, _OPERATION, str(account_id), self.clock)

            audit(
                session,
                actor,
                "com.cuenta.abono",
                entity_type="com_account",
                entity_id=str(account_id),
                summary=f"Abono de {payment.amount} a cuenta #{account_id}",
                detail={
                    "method": payment.method.value,
                    "amount": payment.amount,
                    "balance_after": cuenta.balance,
                },
                clock=self.clock,
            )
            return self._to_view(session, cuenta)

        return run_in_transaction(self.factory, _op)

    def get(self, actor: Actor, account_id: int) -> AccountView:
        def _op(session: Session) -> AccountView:
            cuenta = session.get(Account, account_id)
            if cuenta is None:
                raise NotFound(f"cuenta {account_id} no existe")
            self.authorizer.require(session, actor, _VIEW_PERMISSION[AccountKind(cuenta.kind)])
            return self._to_view(session, cuenta)

        return run_in_transaction(self.factory, _op, readonly=True)

    def list(
        self,
        actor: Actor,
        kind: AccountKind | str,
        *,
        status: AccountStatus | None = None,
        party_id: int | None = None,
        text: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> Page[AccountSummary]:
        account_kind = AccountKind(kind)

        def _op(session: Session) -> Page[AccountSummary]:
            self.authorizer.require(session, actor, _VIEW_PERMISSION[account_kind])
            page_num, size, offset = normalize_page(page, page_size)

            condiciones = [Account.kind == account_kind.value]
            if party_id is not None:
                condiciones.append(Account.party_id == party_id)

            texto = text.strip()
            stmt = select(Account, Party).join(Party, Account.party_id == Party.id)
            if condiciones:
                stmt = stmt.where(and_(*condiciones))
            if texto:
                texto_normalizado = normalize_search(texto)
                stmt = stmt.where(
                    or_(
                        Party.name_search.like(
                            f"%{escape_like(texto_normalizado)}%", escape=LIKE_ESCAPE
                        )
                    )
                )

            filas = session.execute(stmt).all()
            resumenes = [self._to_summary(cuenta, party.name) for cuenta, party in filas]
            if status is not None:
                resumenes = [r for r in resumenes if r.status == status]

            resumenes.sort(key=lambda r: (r.due_date, r.id))
            total = len(resumenes)
            pagina = resumenes[offset : offset + size]

            return Page(items=pagina, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def party_balance(self, actor: Actor, party_id: int, kind: AccountKind | str) -> Decimal:
        account_kind = AccountKind(kind)

        def _op(session: Session) -> Decimal:
            self.authorizer.require(session, actor, _VIEW_PERMISSION[account_kind])
            cuentas = session.scalars(
                select(Account).where(
                    Account.kind == account_kind.value, Account.party_id == party_id
                )
            ).all()
            return money(sum((c.balance for c in cuentas), Decimal("0")))

        return run_in_transaction(self.factory, _op, readonly=True)

    def reconcile(self, session: Session, account_id: int) -> bool:
        """Original menos la suma de abonos debe coincidir con el saldo cacheado."""
        cuenta = session.get(Account, account_id)
        if cuenta is None:
            raise NotFound(f"cuenta {account_id} no existe")
        total_abonos = session.scalars(
            select(AccountPayment.amount).where(AccountPayment.account_id == account_id)
        ).all()
        esperado = money(cuenta.original_amount - sum(total_abonos, Decimal("0")))
        return esperado == cuenta.balance
