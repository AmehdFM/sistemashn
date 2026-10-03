"""Construcción de líneas comerciales desde empaques y medidas de Ferretería."""

from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.models import Product
from sistemashn.comercial.compras.schemas import PurchaseLineInput
from sistemashn.comercial.cotizaciones.schemas import QuoteLineInput
from sistemashn.comercial.presentacion import PresentationSnapshot
from sistemashn.comercial.ventas.schemas import SaleLineInput
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.ferreteria.catalogo.service import FerreteriaCatalogService, PackConversion


def _amount(value: Decimal | int | str, name: str) -> Decimal:
    if isinstance(value, float):
        raise ValidationError(f"{name}: no use float")
    try:
        result = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{name} inválido") from exc
    if not result.is_finite() or result < 0:
        raise ValidationError(f"{name} inválido")
    return result


def _base_amount(amount: Decimal, factor: Decimal, step: Decimal, name: str) -> Decimal:
    base = amount / factor
    if base != base.quantize(step):
        raise ValidationError(
            f"{name} por presentación no puede expresarse exactamente por unidad base"
        )
    return base


def _snapshot(conversion: PackConversion, amount: Decimal) -> PresentationSnapshot:
    return PresentationSnapshot(
        pack_id=conversion.pack_id,
        label=conversion.label,
        factor_base=conversion.factor_base,
        quantity=conversion.quantity_pack,
        unit_amount=amount,
    )


class FerreteriaLineBuilder:
    """Normaliza antes de llamar a los servicios transaccionales de Comercial."""

    def __init__(
        self,
        catalog: FerreteriaCatalogService,
        factory: sessionmaker[Session],
    ) -> None:
        self.catalog = catalog
        self.factory = factory

    def purchase_line(
        self,
        actor: Actor,
        pack_id: int,
        quantity: Decimal | int | str,
        unit_cost_pack: Decimal | int | str,
    ) -> PurchaseLineInput:
        conversion = self.catalog.convert_to_base(actor, pack_id, quantity)
        amount = _amount(unit_cost_pack, "costo")
        base_cost = _base_amount(amount, conversion.factor_base, Decimal("0.0001"), "costo")
        return PurchaseLineInput(
            product_id=conversion.product_id,
            qty=conversion.quantity_base,
            unit_cost=base_cost,
            presentation=_snapshot(conversion, amount),
        )

    def sale_line(
        self,
        actor: Actor,
        pack_id: int,
        quantity: Decimal | int | str,
        unit_price_pack: Decimal | int | str | None = None,
    ) -> SaleLineInput:
        conversion = self.catalog.convert_to_base(actor, pack_id, quantity)
        if unit_price_pack is None and conversion.price is None:
            with session_scope(self.factory, readonly=True) as session:
                product = session.get(Product, conversion.product_id)
                if product is None:
                    raise NotFound(f"producto {conversion.product_id} no existe")
                base_price = product.sale_price
            amount = base_price * conversion.factor_base
        else:
            amount = _amount(
                conversion.price if unit_price_pack is None else unit_price_pack,
                "precio",
            )
            base_price = _base_amount(amount, conversion.factor_base, Decimal("0.01"), "precio")
        return SaleLineInput(
            product_id=conversion.product_id,
            qty=conversion.quantity_base,
            unit_price=base_price,
            presentation=_snapshot(conversion, amount),
        )

    def quote_line(
        self,
        actor: Actor,
        pack_id: int,
        quantity: Decimal | int | str,
        unit_price_pack: Decimal | int | str | None = None,
    ) -> QuoteLineInput:
        line = self.sale_line(actor, pack_id, quantity, unit_price_pack)
        return QuoteLineInput(
            product_id=line.product_id,
            qty=line.qty,
            unit_price=line.unit_price,
            presentation=line.presentation,
        )
