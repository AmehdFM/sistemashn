"""Servicio de devoluciones de cliente y a proveedor (plan T5.2/T5.3).

Simplificaciones deliberadas de esta fase (documentadas también en el reporte de la tarea):

- `reembolso` (cliente o proveedor) no integra automáticamente con `CashService`: solo registra
  el monto y el método de pago en el detalle de auditoría. Conectar el reembolso a un movimiento
  real de caja queda para quien integre la UI, que sí conoce la sesión de caja abierta.
- `cambio` no crea la venta nueva: `customer_return` deja `new_sale_id=None` y expone
  `link_exchange_sale` para asociarla después de que otro flujo (UI + `SaleService`) la confirme.
- `credito_futuro` en una devolución a proveedor reduce el saldo de la CxP de la compra original
  si existe y tiene saldo, por `min(amount, balance)` (ajuste interno, no un abono real con su
  propio `request_id`); si no hay CxP con saldo, crea una nota de crédito de proveedor por el
  monto completo. No reparte el remanente entre ambos mecanismos si el monto de la devolución
  excede el saldo de la CxP: el remanente simplemente no se acredita en esta fase.
- Una devolución a proveedor asume que la pieza defectuosa ya está en `unsellable` (llegó ahí por
  una devolución de cliente no vendible o un defecto detectado en bodega) y sale con
  `InventoryLedger.unsellable_out`. Si el flujo real fuera "defecto detectado en `on_hand`", la UI
  debe primero llamar `InventoryService`/`ledger.move_to_unsellable` (fuera de alcance de este
  servicio).
- Un saldo a favor (`AccountKind.CREDIT_NOTE`) no "vence": se usa `date.max` como `due_date` para
  reutilizar el esquema de `com_account` sin agregar una columna nullable nueva.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.compras.models import Purchase, PurchaseLine
from sistemashn.comercial.credito.models import Account
from sistemashn.comercial.credito.schemas import AccountKind
from sistemashn.comercial.credito.service import AccountService
from sistemashn.comercial.devoluciones.errors import ReturnExceedsOriginal
from sistemashn.comercial.devoluciones.models import CustomerReturn, SupplierReturn
from sistemashn.comercial.devoluciones.schemas import (
    CustomerReturnInput,
    CustomerReturnResolution,
    CustomerReturnView,
    ReturnCondition,
    SupplierReturnInput,
    SupplierReturnResolution,
    SupplierReturnView,
)
from sistemashn.comercial.idempotency import find_previous, remember
from sistemashn.comercial.inventario.kinds import MovementKind
from sistemashn.comercial.inventario.ledger import InventoryLedger
from sistemashn.comercial.ventas.models import Sale, SaleLine
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.money import money
from sistemashn.core.pagination import Page, normalize_page

_PERMISO = "com.devoluciones.gestionar"
_OPERACION_CLIENTE = "devolucion.cliente"
_OPERACION_PROVEEDOR = "devolucion.proveedor"

# Un saldo a favor no vence: se guarda como una fecha lejana para reutilizar `com_account`.
_SIN_VENCIMIENTO = date.max


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ReturnService:
    """Devoluciones de cliente y a proveedor, con su efecto en inventario y cuentas."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime],
        ledger: InventoryLedger,
        accounts: AccountService,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.ledger = ledger
        self.accounts = accounts

    # -- Devolución de cliente ---------------------------------------------------------

    def customer_return(self, actor: Actor, data: CustomerReturnInput) -> CustomerReturnView:
        def _op(session: Session) -> CustomerReturnView:
            self.authorizer.require(session, actor, _PERMISO)

            previo = find_previous(session, data.request_id, _OPERACION_CLIENTE)
            if previo is not None:
                devolucion = session.get(CustomerReturn, int(previo))
                if devolucion is None:
                    raise NotFound(f"devolución {previo} no existe")
                return self._to_customer_view(devolucion)

            sale_line = session.get(SaleLine, data.sale_line_id)
            if sale_line is None:
                raise ValidationError(f"la línea de venta {data.sale_line_id} no existe")
            sale = session.get(Sale, sale_line.sale_id)
            if sale is None or sale.status == "anulada":
                raise ValidationError("no se puede devolver una línea de una venta anulada")

            ya_devuelto = money(
                sum(
                    (
                        session.scalars(
                            select(CustomerReturn.qty).where(
                                CustomerReturn.sale_line_id == data.sale_line_id
                            )
                        ).all()
                    ),
                    Decimal("0"),
                )
            )
            if ya_devuelto + data.qty > sale_line.qty:
                raise ReturnExceedsOriginal(
                    f"la línea {data.sale_line_id} solo tiene {sale_line.qty - ya_devuelto} "
                    "disponible para devolver"
                )

            monto = money(data.qty * sale_line.unit_price)
            ahora = self.clock()

            devolucion = CustomerReturn(
                sale_line_id=data.sale_line_id,
                qty=data.qty,
                condition=data.condition.value,
                resolution=data.resolution.value,
                amount=monto,
                new_sale_id=None,
                user_id=actor.user_id,
                reason=data.reason,
                created_at=ahora,
            )
            session.add(devolucion)
            session.flush()

            if data.condition == ReturnCondition.VENDIBLE:
                self.ledger.receive(
                    session,
                    actor,
                    sale_line.product_id,
                    data.qty,
                    sale_line.unit_cost_snapshot,
                    kind=MovementKind.CUSTOMER_RETURN_SELLABLE,
                    ref_type="customer_return",
                    ref_id=str(devolucion.id),
                    reason=data.reason,
                )
            else:
                self.ledger.move_to_unsellable(
                    session,
                    actor,
                    sale_line.product_id,
                    data.qty,
                    sale_line.unit_cost_snapshot,
                    ref_type="customer_return",
                    ref_id=str(devolucion.id),
                    reason=data.reason,
                )

            if data.resolution == CustomerReturnResolution.SALDO_A_FAVOR:
                if sale.customer_id is None:
                    raise ValidationError("un saldo a favor requiere que la venta tenga un cliente")
                self.accounts.create_account(
                    session,
                    actor,
                    kind=AccountKind.CREDIT_NOTE,
                    party_id=sale.customer_id,
                    source_type="customer_return",
                    source_id=str(devolucion.id),
                    amount=monto,
                    due_date=_SIN_VENCIMIENTO,
                )

            remember(session, data.request_id, _OPERACION_CLIENTE, str(devolucion.id), self.clock)

            audit(
                session,
                actor,
                "com.devolucion_cliente.registrada",
                entity_type="com_customer_return",
                entity_id=str(devolucion.id),
                summary=f"Devolución de cliente #{devolucion.id} por {monto}",
                detail={
                    "sale_line_id": data.sale_line_id,
                    "qty": data.qty,
                    "condition": data.condition.value,
                    "resolution": data.resolution.value,
                    "amount": monto,
                    "payment_method": data.payment.method.value if data.payment else None,
                    "reason": data.reason,
                },
                clock=self.clock,
            )

            return self._to_customer_view(devolucion)

        return run_in_transaction(self.factory, _op)

    def link_exchange_sale(
        self, actor: Actor, return_id: int, new_sale_id: int
    ) -> CustomerReturnView:
        """Asocia la venta de cambio ya confirmada por otro flujo a una devolución existente."""

        def _op(session: Session) -> CustomerReturnView:
            self.authorizer.require(session, actor, _PERMISO)
            devolucion = session.get(CustomerReturn, return_id)
            if devolucion is None:
                raise NotFound(f"devolución {return_id} no existe")
            if devolucion.resolution != CustomerReturnResolution.CAMBIO.value:
                raise ValidationError(f"la devolución {return_id} no tiene resolución 'cambio'")
            venta_nueva = session.get(Sale, new_sale_id)
            if venta_nueva is None:
                raise ValidationError(f"la venta {new_sale_id} no existe")

            devolucion.new_sale_id = new_sale_id
            session.flush()

            audit(
                session,
                actor,
                "com.devolucion_cliente.cambio_enlazado",
                entity_type="com_customer_return",
                entity_id=str(devolucion.id),
                summary=f"Devolución #{devolucion.id} enlazada a venta de cambio {new_sale_id}",
                detail={"new_sale_id": new_sale_id},
                clock=self.clock,
            )
            return self._to_customer_view(devolucion)

        return run_in_transaction(self.factory, _op)

    # -- Devolución a proveedor ---------------------------------------------------------

    def supplier_return(self, actor: Actor, data: SupplierReturnInput) -> SupplierReturnView:
        def _op(session: Session) -> SupplierReturnView:
            self.authorizer.require(session, actor, _PERMISO)

            previo = find_previous(session, data.request_id, _OPERACION_PROVEEDOR)
            if previo is not None:
                devolucion = session.get(SupplierReturn, int(previo))
                if devolucion is None:
                    raise NotFound(f"devolución {previo} no existe")
                return self._to_supplier_view(devolucion)

            purchase_line = session.get(PurchaseLine, data.purchase_line_id)
            if purchase_line is None:
                raise ValidationError(f"la línea de compra {data.purchase_line_id} no existe")
            purchase = session.get(Purchase, purchase_line.purchase_id)
            if purchase is None or purchase.status == "anulada":
                raise ValidationError("no se puede devolver una línea de una compra anulada")

            ya_devuelto = money(
                sum(
                    (
                        session.scalars(
                            select(SupplierReturn.qty).where(
                                SupplierReturn.purchase_line_id == data.purchase_line_id
                            )
                        ).all()
                    ),
                    Decimal("0"),
                )
            )
            if ya_devuelto + data.qty > purchase_line.qty:
                raise ReturnExceedsOriginal(
                    f"la línea {data.purchase_line_id} solo tiene "
                    f"{purchase_line.qty - ya_devuelto} disponible para devolver"
                )

            monto = money(data.qty * purchase_line.unit_cost)
            ahora = self.clock()

            devolucion = SupplierReturn(
                purchase_line_id=data.purchase_line_id,
                qty=data.qty,
                resolution=data.resolution.value,
                amount=monto,
                user_id=actor.user_id,
                reason=data.reason,
                created_at=ahora,
            )
            session.add(devolucion)
            session.flush()

            # Supuesto documentado: la pieza defectuosa devuelta al proveedor ya está en
            # `unsellable` (llegó ahí por una devolución de cliente no vendible o un defecto
            # detectado en bodega, movido con `move_to_unsellable` antes de este flujo).
            self.ledger.unsellable_out(
                session,
                actor,
                purchase_line.product_id,
                data.qty,
                kind=MovementKind.SUPPLIER_RETURN_OUT,
                ref_type="supplier_return",
                ref_id=str(devolucion.id),
                reason=data.reason,
            )

            if data.resolution == SupplierReturnResolution.REEMPLAZO:
                self.ledger.receive(
                    session,
                    actor,
                    purchase_line.product_id,
                    data.qty,
                    purchase_line.unit_cost,
                    kind=MovementKind.PURCHASE_IN,
                    ref_type="supplier_return",
                    ref_id=str(devolucion.id),
                    reason=data.reason,
                )
            elif data.resolution == SupplierReturnResolution.CREDITO_FUTURO:
                self._aplicar_credito_futuro(session, actor, purchase, devolucion, monto)

            remember(session, data.request_id, _OPERACION_PROVEEDOR, str(devolucion.id), self.clock)

            audit(
                session,
                actor,
                "com.devolucion_proveedor.registrada",
                entity_type="com_supplier_return",
                entity_id=str(devolucion.id),
                summary=f"Devolución a proveedor #{devolucion.id} por {monto}",
                detail={
                    "purchase_line_id": data.purchase_line_id,
                    "qty": data.qty,
                    "resolution": data.resolution.value,
                    "amount": monto,
                    "reason": data.reason,
                },
                clock=self.clock,
            )

            return self._to_supplier_view(devolucion)

        return run_in_transaction(self.factory, _op)

    def _aplicar_credito_futuro(
        self,
        session: Session,
        actor: Actor,
        purchase: Purchase,
        devolucion: SupplierReturn,
        monto: Decimal,
    ) -> None:
        cuenta = session.scalar(
            select(Account).where(
                Account.kind == AccountKind.PAYABLE.value,
                Account.source_type == "purchase",
                Account.source_id == str(purchase.id),
            )
        )
        if cuenta is not None and cuenta.balance > 0:
            ajuste = min(monto, cuenta.balance)
            cuenta.balance = money(cuenta.balance - ajuste)
            session.flush()
            audit(
                session,
                actor,
                "com.cuenta.ajuste_devolucion",
                entity_type="com_account",
                entity_id=str(cuenta.id),
                summary=f"Ajuste de {ajuste} en CxP #{cuenta.id} por devolución a proveedor",
                detail={
                    "supplier_return_id": devolucion.id,
                    "amount": ajuste,
                    "balance_after": cuenta.balance,
                },
                clock=self.clock,
            )
            return

        self.accounts.create_account(
            session,
            actor,
            kind=AccountKind.CREDIT_NOTE,
            party_id=purchase.supplier_id,
            source_type="supplier_return",
            source_id=str(devolucion.id),
            amount=monto,
            due_date=_SIN_VENCIMIENTO,
        )

    # -- Consultas ---------------------------------------------------------

    def get_customer_return(self, actor: Actor, return_id: int) -> CustomerReturnView:
        def _op(session: Session) -> CustomerReturnView:
            self.authorizer.require(session, actor, _PERMISO)
            devolucion = session.get(CustomerReturn, return_id)
            if devolucion is None:
                raise NotFound(f"devolución {return_id} no existe")
            return self._to_customer_view(devolucion)

        return run_in_transaction(self.factory, _op, readonly=True)

    def get_supplier_return(self, actor: Actor, return_id: int) -> SupplierReturnView:
        def _op(session: Session) -> SupplierReturnView:
            self.authorizer.require(session, actor, _PERMISO)
            devolucion = session.get(SupplierReturn, return_id)
            if devolucion is None:
                raise NotFound(f"devolución {return_id} no existe")
            return self._to_supplier_view(devolucion)

        return run_in_transaction(self.factory, _op, readonly=True)

    def list_customer_returns(
        self,
        actor: Actor,
        *,
        sale_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Page[CustomerReturnView]:
        def _op(session: Session) -> Page[CustomerReturnView]:
            self.authorizer.require(session, actor, _PERMISO)
            page_num, size, offset = normalize_page(page, page_size)

            stmt = select(CustomerReturn)
            if sale_id is not None:
                stmt = stmt.join(SaleLine, CustomerReturn.sale_line_id == SaleLine.id).where(
                    SaleLine.sale_id == sale_id
                )

            filas = session.scalars(stmt).all()
            items = [self._to_customer_view(f) for f in filas]
            items.sort(key=lambda v: (v.created_at, v.id), reverse=True)

            total = len(items)
            pagina = items[offset : offset + size]
            return Page(items=pagina, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def list_supplier_returns(
        self,
        actor: Actor,
        *,
        purchase_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Page[SupplierReturnView]:
        def _op(session: Session) -> Page[SupplierReturnView]:
            self.authorizer.require(session, actor, _PERMISO)
            page_num, size, offset = normalize_page(page, page_size)

            stmt = select(SupplierReturn)
            if purchase_id is not None:
                stmt = stmt.join(
                    PurchaseLine, SupplierReturn.purchase_line_id == PurchaseLine.id
                ).where(PurchaseLine.purchase_id == purchase_id)

            filas = session.scalars(stmt).all()
            items = [self._to_supplier_view(f) for f in filas]
            items.sort(key=lambda v: (v.created_at, v.id), reverse=True)

            total = len(items)
            pagina = items[offset : offset + size]
            return Page(items=pagina, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos: vistas ---------------------------------------------------------

    def _to_customer_view(self, devolucion: CustomerReturn) -> CustomerReturnView:
        return CustomerReturnView(
            id=devolucion.id,
            sale_line_id=devolucion.sale_line_id,
            qty=devolucion.qty,
            condition=devolucion.condition,
            resolution=devolucion.resolution,
            amount=devolucion.amount,
            new_sale_id=devolucion.new_sale_id,
            user_id=devolucion.user_id,
            reason=devolucion.reason,
            created_at=devolucion.created_at,
        )

    def _to_supplier_view(self, devolucion: SupplierReturn) -> SupplierReturnView:
        return SupplierReturnView(
            id=devolucion.id,
            purchase_line_id=devolucion.purchase_line_id,
            qty=devolucion.qty,
            resolution=devolucion.resolution,
            amount=devolucion.amount,
            user_id=devolucion.user_id,
            reason=devolucion.reason,
            created_at=devolucion.created_at,
        )
