"""Servicio de inventario: ajustes, consulta de existencias y movimientos (plan T2.2)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.models import Product
from sistemashn.comercial.inventario.ledger import InventoryLedger
from sistemashn.comercial.inventario.models import Stock, StockMovement
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.pagination import Page, normalize_page


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class StockView:
    product_id: int
    on_hand: Decimal
    reserved: Decimal
    unsellable: Decimal
    available: Decimal
    avg_cost: Decimal | None
    updated_at: datetime


@dataclass(frozen=True)
class MovementView:
    id: int
    product_id: int
    occurred_at: datetime
    kind: str
    d_on_hand: Decimal
    d_reserved: Decimal
    d_unsellable: Decimal
    unit_cost: Decimal | None
    avg_cost_after: Decimal
    ref_type: str | None
    ref_id: str | None
    user_id: int
    reason: str | None


@dataclass(frozen=True)
class LowStockItem:
    product_id: int
    code: str
    name: str
    on_hand: Decimal
    reserved: Decimal
    available: Decimal
    min_stock: Decimal


def _movement_to_view(movement: StockMovement) -> MovementView:
    return MovementView(
        id=movement.id,
        product_id=movement.product_id,
        occurred_at=movement.occurred_at,
        kind=movement.kind,
        d_on_hand=movement.d_on_hand,
        d_reserved=movement.d_reserved,
        d_unsellable=movement.d_unsellable,
        unit_cost=movement.unit_cost,
        avg_cost_after=movement.avg_cost_after,
        ref_type=movement.ref_type,
        ref_id=movement.ref_id,
        user_id=movement.user_id,
        reason=movement.reason,
    )


class InventoryService:
    """Ajustes de inventario y consulta de existencias/movimientos."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
        ledger: InventoryLedger | None = None,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.ledger = ledger or InventoryLedger(clock=clock)

    def adjust(
        self,
        actor: Actor,
        product_id: int,
        delta: Decimal,
        reason: str,
        *,
        unit_cost: Decimal | None = None,
    ) -> None:
        motivo = reason.strip()
        if len(motivo) < 5:
            raise ValidationError("el motivo del ajuste debe tener al menos 5 caracteres")

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.inventario.ajustar")
            stock = session.get(Stock, product_id)
            if stock is None:
                raise NotFound(f"el producto {product_id} no tiene existencias")

            antes = {"on_hand": stock.on_hand, "avg_cost": stock.avg_cost}

            if delta > 0:
                costo = unit_cost if unit_cost is not None else stock.avg_cost
                self.ledger.adjust_in(session, actor, product_id, delta, costo, motivo)
            elif delta < 0:
                self.ledger.adjust_out(session, actor, product_id, -delta, motivo)
            else:
                raise ValidationError("el ajuste no puede ser cero")

            despues = {"on_hand": stock.on_hand, "avg_cost": stock.avg_cost}

            audit(
                session,
                actor,
                "com.inventario.ajuste",
                entity_type="com_product",
                entity_id=str(product_id),
                summary=f"Ajuste de inventario del producto {product_id}: {motivo}",
                detail={"antes": antes, "despues": despues, "delta": delta, "motivo": motivo},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def stock(self, actor: Actor, product_id: int) -> StockView:
        def _op(session: Session) -> StockView:
            self.authorizer.require(session, actor, "com.inventario.ver")
            stock = session.get(Stock, product_id)
            if stock is None:
                raise NotFound(f"el producto {product_id} no tiene existencias")
            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
            return StockView(
                product_id=stock.product_id,
                on_hand=stock.on_hand,
                reserved=stock.reserved,
                unsellable=stock.unsellable,
                available=stock.on_hand - stock.reserved,
                avg_cost=stock.avg_cost if ver_costos else None,
                updated_at=stock.updated_at,
            )

        return run_in_transaction(self.factory, _op, readonly=True)

    def movements(
        self, actor: Actor, product_id: int, page: int = 1, page_size: int = 50
    ) -> Page[MovementView]:
        def _op(session: Session) -> Page[MovementView]:
            self.authorizer.require(session, actor, "com.inventario.ver")
            page_num, size, offset = normalize_page(page, page_size)
            stmt = select(StockMovement).where(StockMovement.product_id == product_id)
            todos = session.scalars(stmt).all()
            ordenados = sorted(todos, key=lambda m: (m.occurred_at, m.id), reverse=True)
            total = len(ordenados)
            pagina = ordenados[offset : offset + size]
            items = [_movement_to_view(m) for m in pagina]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def low_stock(self, actor: Actor, page: int = 1, page_size: int = 50) -> Page[LowStockItem]:
        def _op(session: Session) -> Page[LowStockItem]:
            self.authorizer.require(session, actor, "com.inventario.ver")
            page_num, size, offset = normalize_page(page, page_size)
            stmt = (
                select(Product, Stock)
                .join(Stock, Stock.product_id == Product.id)
                .where(
                    Product.active.is_(True),
                    Product.is_kit.is_(False),
                    Product.min_stock > 0,
                )
            )
            filas = session.execute(stmt).all()
            bajos = [
                (producto, stock)
                for producto, stock in filas
                if (stock.on_hand - stock.reserved) <= producto.min_stock
            ]
            bajos.sort(key=lambda par: par[0].code)
            total = len(bajos)
            pagina = bajos[offset : offset + size]
            items = [
                LowStockItem(
                    product_id=producto.id,
                    code=producto.code,
                    name=producto.name,
                    on_hand=stock.on_hand,
                    reserved=stock.reserved,
                    available=stock.on_hand - stock.reserved,
                    min_stock=producto.min_stock,
                )
                for producto, stock in pagina
            ]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def reconcile(self, session: Session, product_id: int) -> bool:
        """Verifica que la suma de deltas de movimientos coincida con el saldo de `com_stock`."""
        stock = session.get(Stock, product_id)
        if stock is None:
            raise NotFound(f"el producto {product_id} no tiene existencias")

        movimientos = session.scalars(
            select(StockMovement).where(StockMovement.product_id == product_id)
        ).all()

        suma_on_hand = sum((m.d_on_hand for m in movimientos), Decimal("0"))
        suma_reserved = sum((m.d_reserved for m in movimientos), Decimal("0"))
        suma_unsellable = sum((m.d_unsellable for m in movimientos), Decimal("0"))

        return (
            suma_on_hand == stock.on_hand
            and suma_reserved == stock.reserved
            and suma_unsellable == stock.unsellable
        )
