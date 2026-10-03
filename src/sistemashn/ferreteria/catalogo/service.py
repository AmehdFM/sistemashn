"""Catálogo ferrotero y conversión exacta a la unidad base del SKU."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.models import Product, Unit
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.ferreteria.catalogo.models import FerItem, FerPack

_QUANTITY_STEP = Decimal("0.001")
_MONEY_STEP = Decimal("0.01")
_MAX_SQLITE_INTEGER = 2**63 - 1


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _decimal(value: Decimal | int | str, field: str) -> Decimal:
    if isinstance(value, float):
        raise ValidationError(f"{field}: use Decimal, entero o texto; float no permitido")
    try:
        number = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{field} inválido") from exc
    if not number.is_finite():
        raise ValidationError(f"{field} debe ser finito")
    return number


def _exact_step(value: Decimal, step: Decimal, field: str) -> None:
    if value != value.quantize(step):
        raise ValidationError(f"{field} excede la precisión permitida de {step}")


def _text(value: str | None, limit: int, field: str) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if len(trimmed) > limit:
        raise ValidationError(f"{field} supera {limit} caracteres")
    return trimmed or None


@dataclass(frozen=True)
class FerItemView:
    product_id: int
    brand: str | None
    family: str | None
    specs: str | None


@dataclass(frozen=True)
class FerPackView:
    id: int
    product_id: int
    code: str | None
    label: str
    factor_base: Decimal
    permits_fraction: bool
    price: Decimal | None
    active: bool


@dataclass(frozen=True)
class PackConversion:
    """Snapshot para construir una línea; aún no realiza movimientos ni cobros."""

    pack_id: int
    product_id: int
    label: str
    factor_base: Decimal
    quantity_pack: Decimal
    quantity_base: Decimal
    price: Decimal | None


def _pack_view(pack: FerPack) -> FerPackView:
    return FerPackView(
        id=pack.id,
        product_id=pack.product_id,
        code=pack.code,
        label=pack.label,
        factor_base=Decimal(pack.factor_numerator) / Decimal(pack.factor_denominator),
        permits_fraction=pack.permits_fraction,
        price=pack.price,
        active=pack.active,
    )


class FerreteriaCatalogService:
    """Gestiona ficha y empaque; mantiene el stock en `comercial/inventario`."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    def get_item(self, actor: Actor, product_id: int) -> FerItemView | None:
        def _op(session: Session) -> FerItemView | None:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            item = session.get(FerItem, product_id)
            if item is None:
                return None
            return FerItemView(item.product_id, item.brand, item.family, item.specs)

        return run_in_transaction(self.factory, _op, readonly=True)

    def set_item(
        self,
        actor: Actor,
        product_id: int,
        *,
        brand: str | None = None,
        family: str | None = None,
        specs: str | None = None,
    ) -> None:
        brand = _text(brand, 100, "marca")
        family = _text(family, 100, "familia")
        specs = _text(specs, 2000, "especificaciones")

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "fer.catalogo.gestionar")
            product = session.get(Product, product_id)
            if product is None:
                raise NotFound(f"producto {product_id} no existe")
            item = session.get(FerItem, product_id)
            if item is None:
                item = FerItem(product_id=product_id)
                session.add(item)
            item.brand, item.family, item.specs = brand, family, specs
            session.flush()
            audit(
                session,
                actor,
                "fer.item.actualizado",
                entity_type="fer_item",
                entity_id=str(product_id),
                summary=f"Ficha de Ferretería '{product.code}' actualizada",
                detail={"brand": brand, "family": family, "specs": specs},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def list_packs(
        self, actor: Actor, product_id: int, *, include_inactive: bool = False
    ) -> list[FerPackView]:
        def _op(session: Session) -> list[FerPackView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            if session.get(Product, product_id) is None:
                raise NotFound(f"producto {product_id} no existe")
            query = select(FerPack).where(FerPack.product_id == product_id)
            if not include_inactive:
                query = query.where(FerPack.active.is_(True))
            return [_pack_view(pack) for pack in session.scalars(query.order_by(FerPack.id))]

        return run_in_transaction(self.factory, _op, readonly=True)

    def create_pack(
        self,
        actor: Actor,
        product_id: int,
        *,
        code: str | None,
        label: str,
        factor_base: Decimal | int | str,
        permits_fraction: bool,
        price: Decimal | int | str | None = None,
    ) -> int:
        code = _text(code, 64, "código")
        label = _text(label, 100, "etiqueta")
        if label is None:
            raise ValidationError("etiqueta de presentación requerida")
        factor = _decimal(factor_base, "factor")
        if factor <= 0:
            raise ValidationError("factor debe ser positivo")
        numerator, denominator = factor.as_integer_ratio()
        if numerator > _MAX_SQLITE_INTEGER or denominator > _MAX_SQLITE_INTEGER:
            raise ValidationError("factor excede el rango representable")
        pack_price = None if price is None else _decimal(price, "precio")
        if pack_price is not None:
            if pack_price < 0:
                raise ValidationError("precio no puede ser negativo")
            _exact_step(pack_price, _MONEY_STEP, "precio")

        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "fer.catalogo.gestionar")
            product = session.get(Product, product_id)
            if product is None:
                raise NotFound(f"producto {product_id} no existe")
            if product.is_kit:
                raise ValidationError("un kit no puede tener presentaciones de inventario")
            unit = session.get(Unit, product.unit_id)
            if unit is None:
                raise ValidationError("unidad base inexistente")
            # Una presentación sellada de unidad indivisible debe contener piezas completas.
            if not unit.allows_fraction and factor != factor.to_integral_value():
                raise ValidationError("factor genera fracciones de una unidad indivisible")
            if code is not None:
                if (
                    session.scalar(
                        select(Product.id).where(or_(Product.code == code, Product.barcode == code))
                    )
                    is not None
                ):
                    raise ValidationError("código ya usado por un producto")
                if session.scalar(select(FerPack.id).where(FerPack.code == code)) is not None:
                    raise ValidationError("código de presentación duplicado")
            if (
                session.scalar(
                    select(FerPack.id).where(
                        FerPack.product_id == product_id, FerPack.label == label
                    )
                )
                is not None
            ):
                raise ValidationError("etiqueta de presentación duplicada para este producto")
            pack = FerPack(
                product_id=product_id,
                code=code,
                label=label,
                factor_numerator=numerator,
                factor_denominator=denominator,
                permits_fraction=permits_fraction,
                price=pack_price,
                active=True,
            )
            session.add(pack)
            session.flush()
            audit(
                session,
                actor,
                "fer.pack.creado",
                entity_type="fer_pack",
                entity_id=str(pack.id),
                summary=f"Presentación '{label}' de '{product.code}' creada",
                detail={"factor_base": str(factor), "code": code},
                clock=self.clock,
            )
            return pack.id

        return run_in_transaction(self.factory, _op)

    def set_pack_active(self, actor: Actor, pack_id: int, active: bool) -> None:
        """Desactiva/reactiva una presentación sin alterar líneas ya confirmadas."""

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "fer.catalogo.gestionar")
            pack = session.get(FerPack, pack_id)
            if pack is None:
                raise NotFound(f"presentación {pack_id} no existe")
            if pack.active == active:
                return
            pack.active = active
            audit(
                session,
                actor,
                "fer.pack.activado" if active else "fer.pack.desactivado",
                entity_type="fer_pack",
                entity_id=str(pack.id),
                summary=f"Presentación '{pack.label}' {'activada' if active else 'desactivada'}",
                detail={"product_id": pack.product_id, "active": active},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def convert_to_base(
        self, actor: Actor, pack_id: int, quantity: Decimal | int | str
    ) -> PackConversion:
        original = _decimal(quantity, "cantidad")
        if original <= 0:
            raise ValidationError("cantidad debe ser positiva")
        _exact_step(original, _QUANTITY_STEP, "cantidad de presentación")

        def _op(session: Session) -> PackConversion:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            pack = session.get(FerPack, pack_id)
            if pack is None or not pack.active:
                raise NotFound(f"presentación {pack_id} no existe o está inactiva")
            product = session.get(Product, pack.product_id)
            if product is None or not product.active:
                raise ValidationError("producto inactivo")
            unit = session.get(Unit, product.unit_id)
            if unit is None or not unit.active:
                raise ValidationError("unidad base inactiva")
            if not pack.permits_fraction and original != original.to_integral_value():
                raise ValidationError("esta presentación solo admite cantidades enteras")
            factor = Decimal(pack.factor_numerator) / Decimal(pack.factor_denominator)
            base = original * factor
            _exact_step(base, _QUANTITY_STEP, "cantidad base")
            if not unit.allows_fraction and base != base.to_integral_value():
                raise ValidationError("unidad base indivisible")
            return PackConversion(
                pack_id=pack.id,
                product_id=pack.product_id,
                label=pack.label,
                factor_base=factor,
                quantity_pack=original,
                quantity_base=base,
                price=pack.price,
            )

        return run_in_transaction(self.factory, _op, readonly=True)

    def resolve_barcode(self, actor: Actor, code: str) -> FerPackView | None:
        code = _text(code, 64, "código")
        if code is None:
            return None

        def _op(session: Session) -> FerPackView | None:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            pack = session.scalar(
                select(FerPack).where(FerPack.code == code, FerPack.active.is_(True))
            )
            return None if pack is None else _pack_view(pack)

        return run_in_transaction(self.factory, _op, readonly=True)
