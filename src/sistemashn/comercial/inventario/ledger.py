"""Libro de inventario: única fuente de verdad de existencias (plan T2.2).

API interna: recibe la `session` de la operación de negocio que la llama, no abre
transacciones propias, no verifica permisos ni audita (eso lo hace el servicio llamador)
y nunca hace commit.
"""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from sistemashn.comercial.catalogo.models import Product, Unit
from sistemashn.comercial.inventario.errors import InsufficientStock, InvalidQuantity
from sistemashn.comercial.inventario.kinds import MovementKind
from sistemashn.comercial.inventario.models import Stock, StockMovement
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.money import qty
from sistemashn.core.money import unit_cost as quantize_unit_cost


class InventoryLedger:
    """Movimientos atómicos de existencias sobre `com_stock` / `com_stock_movement`."""

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self.clock = clock

    # -- Entradas -----------------------------------------------------------

    def receive(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_in: Decimal,
        unit_cost: Decimal,
        *,
        kind: MovementKind = MovementKind.PURCHASE_IN,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> Decimal:
        """Entrada de mercadería vendible; devuelve el nuevo costo promedio."""
        cantidad = self._validar_cantidad(session, product_id, qty_in)
        stock = self._get_stock(session, product_id)
        costo = quantize_unit_cost(unit_cost)

        if stock.on_hand <= 0:
            nuevo_promedio = costo
        else:
            total = stock.on_hand * stock.avg_cost + cantidad * costo
            nuevo_promedio = quantize_unit_cost(total / (stock.on_hand + cantidad))

        stock.on_hand += cantidad
        stock.avg_cost = nuevo_promedio
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            kind,
            d_on_hand=cantidad,
            unit_cost=costo,
            avg_cost_after=nuevo_promedio,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )
        return nuevo_promedio

    # -- Salidas --------------------------------------------------------

    def issue(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_out: Decimal,
        *,
        kind: MovementKind = MovementKind.SALE_OUT,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> Decimal:
        """Salida de mercadería vendible; devuelve el costo promedio aplicado."""
        cantidad = self._validar_cantidad(session, product_id, qty_out)
        stock = self._get_stock(session, product_id)
        disponible = stock.on_hand - stock.reserved
        if cantidad > disponible:
            raise InsufficientStock(product_id, disponible, cantidad)

        stock.on_hand -= cantidad
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            kind,
            d_on_hand=-cantidad,
            avg_cost_after=stock.avg_cost,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )
        return stock.avg_cost

    # -- Apartados --------------------------------------------------------

    def reserve(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_reserve: Decimal,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        cantidad = self._validar_cantidad(session, product_id, qty_reserve)
        stock = self._get_stock(session, product_id)
        disponible = stock.on_hand - stock.reserved
        if cantidad > disponible:
            raise InsufficientStock(product_id, disponible, cantidad)

        stock.reserved += cantidad
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            MovementKind.RESERVE,
            d_reserved=cantidad,
            avg_cost_after=stock.avg_cost,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    def release(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_release: Decimal,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        cantidad = self._validar_cantidad(session, product_id, qty_release)
        stock = self._get_stock(session, product_id)
        if cantidad > stock.reserved:
            raise InsufficientStock(product_id, stock.reserved, cantidad)

        stock.reserved -= cantidad
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            MovementKind.RELEASE,
            d_reserved=-cantidad,
            avg_cost_after=stock.avg_cost,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    def issue_reserved(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_issue: Decimal,
        *,
        kind: MovementKind = MovementKind.SALE_OUT,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> Decimal:
        """Consume apartado; devuelve el costo promedio aplicado."""
        cantidad = self._validar_cantidad(session, product_id, qty_issue)
        stock = self._get_stock(session, product_id)
        if cantidad > stock.reserved:
            raise InsufficientStock(product_id, stock.reserved, cantidad)

        stock.reserved -= cantidad
        stock.on_hand -= cantidad
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            kind,
            d_on_hand=-cantidad,
            d_reserved=-cantidad,
            avg_cost_after=stock.avg_cost,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )
        return stock.avg_cost

    # -- Mercadería no vendible ---------------------------------------------

    def move_to_unsellable(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_in: Decimal,
        unit_cost: Decimal,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Devolución de cliente defectuosa: entra a `unsellable`, no afecta `on_hand`."""
        cantidad = self._validar_cantidad(session, product_id, qty_in)
        stock = self._get_stock(session, product_id)
        costo = quantize_unit_cost(unit_cost)

        stock.unsellable += cantidad
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            MovementKind.CUSTOMER_RETURN_UNSELLABLE,
            d_unsellable=cantidad,
            unit_cost=costo,
            avg_cost_after=stock.avg_cost,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    def unsellable_out(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_out: Decimal,
        *,
        kind: MovementKind = MovementKind.SUPPLIER_RETURN_OUT,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Sale mercadería defectuosa (devolución a proveedor o descarte)."""
        cantidad = self._validar_cantidad(session, product_id, qty_out)
        stock = self._get_stock(session, product_id)
        if cantidad > stock.unsellable:
            raise InsufficientStock(product_id, stock.unsellable, cantidad)

        stock.unsellable -= cantidad
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            kind,
            d_unsellable=-cantidad,
            avg_cost_after=stock.avg_cost,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    def unsellable_to_sellable(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_in: Decimal,
        unit_cost: Decimal,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> Decimal:
        """Mercadería antes defectuosa resulta vendible: entra a `on_hand`."""
        cantidad = self._validar_cantidad(session, product_id, qty_in)
        stock = self._get_stock(session, product_id)
        if cantidad > stock.unsellable:
            raise InsufficientStock(product_id, stock.unsellable, cantidad)
        costo = quantize_unit_cost(unit_cost)

        if stock.on_hand <= 0:
            nuevo_promedio = costo
        else:
            total = stock.on_hand * stock.avg_cost + cantidad * costo
            nuevo_promedio = quantize_unit_cost(total / (stock.on_hand + cantidad))

        stock.unsellable -= cantidad
        stock.on_hand += cantidad
        stock.avg_cost = nuevo_promedio
        stock.updated_at = self.clock()

        self._registrar(
            session,
            actor,
            product_id,
            MovementKind.UNSELLABLE_RESOLVED,
            d_on_hand=cantidad,
            d_unsellable=-cantidad,
            unit_cost=costo,
            avg_cost_after=nuevo_promedio,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )
        return nuevo_promedio

    # -- Anulaciones --------------------------------------------------------

    def void_reversal_of_receive(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_value: Decimal,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> Decimal:
        """Revierte una ENTRADA previa (p. ej. anular una compra).

        Decisión de diseño (T5.1): el promedio ponderado ya mezcló esa entrada con el stock
        previo y es irreversible en general si hubo movimientos intermedios (no se puede
        deshacer matemáticamente "como si nunca hubiera entrado"); por eso revertir una entrada
        es simplemente una SALIDA de esa cantidad al costo promedio ACTUAL, reutilizando `issue`
        (sin exigir apartado) con `kind=VOID_REVERSAL`.
        """
        return self.issue(
            session,
            actor,
            product_id,
            qty_value,
            kind=MovementKind.VOID_REVERSAL,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    def void_reversal_of_issue(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_value: Decimal,
        unit_cost: Decimal,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
        reason: str | None = None,
    ) -> Decimal:
        """Revierte una SALIDA previa (p. ej. anular una venta): entra esa cantidad al costo
        unitario que se aplicó en la operación original (`unit_cost_snapshot` de la línea),
        reutilizando `receive` (misma fórmula de promedio ponderado) con `kind=VOID_REVERSAL`.
        """
        return self.receive(
            session,
            actor,
            product_id,
            qty_value,
            unit_cost,
            kind=MovementKind.VOID_REVERSAL,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    # -- Ajustes --------------------------------------------------------

    def adjust_in(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_in: Decimal,
        unit_cost: Decimal,
        reason: str,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
    ) -> Decimal:
        return self.receive(
            session,
            actor,
            product_id,
            qty_in,
            unit_cost,
            kind=MovementKind.ADJUSTMENT_IN,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    def adjust_out(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        qty_out: Decimal,
        reason: str,
        *,
        ref_type: str | None = None,
        ref_id: str | None = None,
    ) -> Decimal:
        return self.issue(
            session,
            actor,
            product_id,
            qty_out,
            kind=MovementKind.ADJUSTMENT_OUT,
            ref_type=ref_type,
            ref_id=ref_id,
            reason=reason,
        )

    # -- Internos ---------------------------------------------------------

    def _validar_cantidad(self, session: Session, product_id: int, qty_value: Decimal) -> Decimal:
        product = session.get(Product, product_id)
        if product is None:
            raise NotFound(f"producto {product_id} no existe")
        if product.is_kit:
            raise ValidationError("los kits no tienen existencias propias")

        cantidad = qty(qty_value)
        if cantidad <= 0:
            raise InvalidQuantity(f"la cantidad debe ser positiva: {cantidad}")

        unit = session.get(Unit, product.unit_id)
        if (
            unit is not None
            and not unit.allows_fraction
            and cantidad != cantidad.to_integral_value()
        ):
            raise InvalidQuantity(f"la unidad '{unit.code}' no admite fracciones: {cantidad}")
        return cantidad

    def _get_stock(self, session: Session, product_id: int) -> Stock:
        stock = session.get(Stock, product_id)
        if stock is None:
            raise NotFound(f"el producto {product_id} no tiene existencias")
        return stock

    def _registrar(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        kind: MovementKind,
        *,
        d_on_hand: Decimal = Decimal("0"),
        d_reserved: Decimal = Decimal("0"),
        d_unsellable: Decimal = Decimal("0"),
        unit_cost: Decimal | None = None,
        avg_cost_after: Decimal,
        ref_type: str | None,
        ref_id: str | None,
        reason: str | None,
    ) -> None:
        session.add(
            StockMovement(
                product_id=product_id,
                occurred_at=self.clock(),
                kind=kind.value,
                d_on_hand=d_on_hand,
                d_reserved=d_reserved,
                d_unsellable=d_unsellable,
                unit_cost=unit_cost,
                avg_cost_after=avg_cost_after,
                ref_type=ref_type,
                ref_id=ref_id,
                user_id=actor.user_id,
                reason=reason,
            )
        )
        session.flush()
