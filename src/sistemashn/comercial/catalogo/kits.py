"""Kits: productos compuestos por otros productos del catálogo (plan T2.3).

Un kit (`Product.is_kit=True`) no tiene fila de existencias propia; su composición vive en
`com_kit_component`. `availability` y `explode` son funciones internas (reciben la `session` de
la operación de negocio, sin permisos ni transacción propia) que usará el servicio de ventas para
expandir el kit sin mover inventario: la venta hace `InventoryLedger.issue` por cada línea.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, select
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from sistemashn.comercial.catalogo.models import Product, Unit
from sistemashn.comercial.inventario.models import Stock
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.base import Base
from sistemashn.core.db.types import Quantity
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.money import qty as quantize_qty


def _utcnow() -> datetime:
    return datetime.now(UTC)


class KitComponent(Base):
    """Cuánto de `component_id` lleva el kit `kit_id`."""

    __tablename__ = "com_kit_component"
    __table_args__ = (
        CheckConstraint("qty > 0", name="kit_component_qty_positiva"),
        CheckConstraint("kit_id != component_id", name="kit_component_no_autorreferencia"),
    )

    kit_id: Mapped[int] = mapped_column(Integer, ForeignKey("com_product.id"), primary_key=True)
    component_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("com_product.id"), primary_key=True
    )
    qty: Mapped[object] = mapped_column(Quantity(), nullable=False)


@dataclass(frozen=True)
class KitComponentView:
    component_id: int
    code: str
    name: str
    qty: Decimal


@dataclass(frozen=True)
class KitLine:
    component_id: int
    qty: Decimal
    avg_cost: Decimal


class KitService:
    """Composición de kits: alta/edición (con permiso) y consulta."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    def set_components(
        self, actor: Actor, kit_id: int, components: list[tuple[int, Decimal]]
    ) -> None:
        """Reemplaza la composición completa del kit; audita antes/después."""

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.catalogo.gestionar")
            kit = session.get(Product, kit_id)
            if kit is None:
                raise NotFound(f"producto {kit_id} no existe")
            if not kit.is_kit:
                raise ValidationError(f"el producto '{kit.code}' no es un kit")
            if not components:
                raise ValidationError("el kit debe tener al menos un componente")

            vistos: set[int] = set()
            filas: list[KitComponent] = []
            for component_id, cantidad in components:
                if component_id == kit_id:
                    raise ValidationError("un kit no puede tener como componente a sí mismo")
                if component_id in vistos:
                    raise ValidationError(f"componente {component_id} repetido")
                vistos.add(component_id)

                componente = session.get(Product, component_id)
                if componente is None:
                    raise NotFound(f"producto {component_id} no existe")
                if not componente.active:
                    raise ValidationError(f"el producto '{componente.code}' está inactivo")
                if componente.is_kit:
                    raise ValidationError(
                        f"el producto '{componente.code}' es un kit: no se admite anidación"
                    )

                cantidad_q = quantize_qty(cantidad)
                if cantidad_q <= 0:
                    raise ValidationError("la cantidad del componente debe ser positiva")
                unit = session.get(Unit, componente.unit_id)
                if (
                    unit is not None
                    and not unit.allows_fraction
                    and cantidad_q != cantidad_q.to_integral_value()
                ):
                    raise ValidationError(
                        f"la unidad '{unit.code}' no admite fracciones: {cantidad_q}"
                    )
                filas.append(KitComponent(kit_id=kit_id, component_id=component_id, qty=cantidad_q))

            antes = self._components_detail(session, kit_id)

            session.query(KitComponent).filter(KitComponent.kit_id == kit_id).delete()
            session.flush()
            for fila in filas:
                session.add(fila)
            session.flush()

            despues = self._components_detail(session, kit_id)

            audit(
                session,
                actor,
                "com.kit.composicion",
                entity_type="com_product",
                entity_id=str(kit_id),
                summary=f"Composición del kit '{kit.code}' actualizada",
                detail={"antes": antes, "despues": despues},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def components(self, actor: Actor, kit_id: int) -> list[KitComponentView]:
        def _op(session: Session) -> list[KitComponentView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            return self._components_views(session, kit_id)

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos -----------------------------------------------------------

    def _components_views(self, session: Session, kit_id: int) -> list[KitComponentView]:
        filas = session.scalars(select(KitComponent).where(KitComponent.kit_id == kit_id)).all()
        vistas = []
        for fila in filas:
            producto = session.get(Product, fila.component_id)
            vistas.append(
                KitComponentView(
                    component_id=fila.component_id,
                    code=producto.code if producto else "",
                    name=producto.name if producto else "",
                    qty=fila.qty,
                )
            )
        return vistas

    def _components_detail(self, session: Session, kit_id: int) -> dict[int, str]:
        filas = session.scalars(select(KitComponent).where(KitComponent.kit_id == kit_id)).all()
        return {str(fila.component_id): str(fila.qty) for fila in filas}


def availability(session: Session, kit_id: int) -> Decimal:
    """Unidades enteras de kit disponibles con las existencias actuales de sus componentes.

    Función interna (sin permisos ni transacción propia) para el servicio de ventas.
    """
    filas = session.scalars(select(KitComponent).where(KitComponent.kit_id == kit_id)).all()
    if not filas:
        return Decimal("0")

    minimo: Decimal | None = None
    for fila in filas:
        stock = session.get(Stock, fila.component_id)
        disponible = stock.on_hand - stock.reserved if stock is not None else Decimal("0")
        posibles = disponible / fila.qty
        if minimo is None or posibles < minimo:
            minimo = posibles

    assert minimo is not None
    return minimo.to_integral_value(rounding=ROUND_DOWN)


def explode(session: Session, kit_id: int, qty_kit: Decimal) -> list[KitLine]:
    """Expande un kit en líneas de componentes para la venta, sin mover inventario.

    Función interna (sin permisos ni transacción propia): la venta hace `InventoryLedger.issue`
    por cada línea dentro de su propia transacción.
    """
    cantidad = quantize_qty(qty_kit)
    if cantidad <= 0:
        raise ValidationError("la cantidad del kit debe ser positiva")
    if cantidad != cantidad.to_integral_value():
        raise ValidationError("la cantidad del kit debe ser entera")

    filas = session.scalars(select(KitComponent).where(KitComponent.kit_id == kit_id)).all()

    lineas = []
    for fila in filas:
        stock = session.get(Stock, fila.component_id)
        avg_cost = stock.avg_cost if stock is not None else Decimal("0")
        lineas.append(
            KitLine(
                component_id=fila.component_id,
                qty=quantize_qty(cantidad * fila.qty),
                avg_cost=avg_cost,
            )
        )
    return lineas
