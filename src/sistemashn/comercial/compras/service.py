"""Servicio de compras: confirmación, consultas e historial de precios (plan T3.2)."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.models import Product
from sistemashn.comercial.catalogo.search import normalize_search
from sistemashn.comercial.compras.errors import InvalidPurchaseLine, PaymentsExceedTotal
from sistemashn.comercial.compras.models import (
    Purchase,
    PurchaseLine,
    PurchasePayment,
    SupplierPrice,
)
from sistemashn.comercial.compras.schemas import (
    PurchaseInput,
    PurchaseLineView,
    PurchasePaymentView,
    PurchaseSummary,
    PurchaseView,
    SupplierPriceView,
)
from sistemashn.comercial.contrapartes.models import Party
from sistemashn.comercial.credito.models import Account
from sistemashn.comercial.credito.schemas import AccountKind
from sistemashn.comercial.credito.service import AccountService
from sistemashn.comercial.idempotency import find_previous, remember
from sistemashn.comercial.inventario.ledger import InventoryLedger
from sistemashn.comercial.presentacion import PresentationSnapshot
from sistemashn.comercial.sequences import format_number, next_number
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.text import LIKE_ESCAPE, escape_like
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.money import money
from sistemashn.core.pagination import Page, normalize_page

_OPERATION = "compra.confirmar"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PurchaseService:
    """Confirmación de compras, consultas e historial de precios por proveedor."""

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

    # -- Confirmación ---------------------------------------------------------

    def confirm(self, actor: Actor, data: PurchaseInput) -> PurchaseView:
        def _op(session: Session) -> PurchaseView:
            self.authorizer.require(session, actor, "com.compras.registrar")

            previo = find_previous(session, data.request_id, _OPERATION)
            if previo is not None:
                purchase = session.get(Purchase, int(previo))
                if purchase is None:
                    raise NotFound(f"compra {previo} no existe")
                ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
                return self._to_view(session, purchase, ver_costos)

            proveedor = session.get(Party, data.supplier_id)
            if proveedor is None:
                raise ValidationError(f"proveedor {data.supplier_id} no existe")
            if not proveedor.active:
                raise ValidationError(f"la contraparte '{proveedor.name}' está inactiva")
            if not proveedor.is_supplier:
                raise ValidationError(f"la contraparte '{proveedor.name}' no es proveedor")

            # Se validan y calculan TODAS las líneas antes de mutar cualquier estado: si una
            # falla, no debe quedar rastro de las anteriores.
            lineas_calculadas: list[dict] = []
            for indice, linea in enumerate(data.lines, start=1):
                product = session.get(Product, linea.product_id)
                if product is None:
                    raise InvalidPurchaseLine(f"producto {linea.product_id} no existe")
                if not product.active:
                    raise InvalidPurchaseLine(f"el producto '{product.code}' está inactivo")
                if product.is_kit:
                    raise InvalidPurchaseLine(
                        f"el producto '{product.code}' es un kit: no tiene existencias propias"
                    )

                tasa = linea.tax_rate if linea.tax_rate is not None else product.tax_rate
                subtotal = money(linea.qty * linea.unit_cost)
                impuesto = money(subtotal * tasa)
                total_linea = money(subtotal + impuesto)

                lineas_calculadas.append(
                    {
                        "line_no": indice,
                        "product": product,
                        "qty": linea.qty,
                        "unit_cost": linea.unit_cost,
                        "tax_rate": tasa,
                        "subtotal": subtotal,
                        "tax": impuesto,
                        "total": total_linea,
                        "presentation": linea.presentation,
                    }
                )

            subtotal_compra = money(sum((li["subtotal"] for li in lineas_calculadas), Decimal("0")))
            tax_total = money(sum((li["tax"] for li in lineas_calculadas), Decimal("0")))
            total_compra = money(subtotal_compra + tax_total)

            pagado = money(sum((p.amount for p in data.payments), Decimal("0")))
            if pagado > total_compra:
                raise PaymentsExceedTotal(
                    f"los pagos ({pagado}) exceden el total de la compra ({total_compra})"
                )

            credito = money(total_compra - pagado)
            if credito > 0:
                if data.credit_due_date is None:
                    raise ValidationError("una compra a crédito requiere fecha de vencimiento")
                fecha_compra = self.clock().date()
                if data.credit_due_date < fecha_compra:
                    raise ValidationError(
                        "la fecha de vencimiento no puede ser anterior a la fecha de compra"
                    )

            numero = format_number("C", next_number(session, "compra"))
            ahora = self.clock()

            purchase = Purchase(
                uuid=uuid4().hex,
                number=numero,
                supplier_id=data.supplier_id,
                supplier_invoice_ref=data.supplier_invoice_ref,
                purchased_at=ahora,
                subtotal=subtotal_compra,
                tax_total=tax_total,
                total=total_compra,
                paid_initial=pagado,
                credit_amount=credito,
                status="confirmada",
                user_id=actor.user_id,
                notes=data.notes,
                created_at=ahora,
            )
            session.add(purchase)
            session.flush()

            for li in lineas_calculadas:
                product = li["product"]
                session.add(
                    PurchaseLine(
                        purchase_id=purchase.id,
                        line_no=li["line_no"],
                        product_id=product.id,
                        description_snapshot=(
                            f"{product.name} · {li['presentation'].quantity} × "
                            f"{li['presentation'].label}"
                        )[:200]
                        if li["presentation"] is not None
                        else product.name,
                        qty=li["qty"],
                        unit_cost=li["unit_cost"],
                        tax_rate=li["tax_rate"],
                        line_subtotal=li["subtotal"],
                        line_tax=li["tax"],
                        line_total=li["total"],
                        presentation_snapshot=(
                            li["presentation"].model_dump_json()
                            if li["presentation"] is not None
                            else None
                        ),
                    )
                )
                self.ledger.receive(
                    session,
                    actor,
                    product.id,
                    li["qty"],
                    li["unit_cost"],
                    ref_type="purchase",
                    ref_id=str(purchase.id),
                )
                session.add(
                    SupplierPrice(
                        supplier_id=data.supplier_id,
                        product_id=product.id,
                        unit_cost=li["unit_cost"],
                        purchase_id=purchase.id,
                        recorded_at=ahora,
                    )
                )

            for pago in data.payments:
                session.add(
                    PurchasePayment(
                        purchase_id=purchase.id,
                        method=pago.method.value,
                        amount=pago.amount,
                        reference=pago.reference,
                    )
                )
            session.flush()

            if credito > 0:
                self.accounts.create_account(
                    session,
                    actor,
                    kind=AccountKind.PAYABLE,
                    party_id=data.supplier_id,
                    source_type="purchase",
                    source_id=str(purchase.id),
                    amount=credito,
                    due_date=data.credit_due_date,  # type: ignore[arg-type]
                )

            remember(session, data.request_id, _OPERATION, str(purchase.id), self.clock)

            audit(
                session,
                actor,
                "com.compra.confirmada",
                entity_type="com_purchase",
                entity_id=str(purchase.id),
                summary=f"Compra {numero} confirmada por {total_compra}",
                detail={
                    "number": numero,
                    "supplier_id": data.supplier_id,
                    "subtotal": subtotal_compra,
                    "tax_total": tax_total,
                    "total": total_compra,
                    "paid_initial": pagado,
                    "credit_amount": credito,
                },
                clock=self.clock,
            )

            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
            return self._to_view(session, purchase, ver_costos)

        return run_in_transaction(self.factory, _op)

    # -- Anulación ---------------------------------------------------------

    def void(self, actor: Actor, purchase_id: int, reason: str) -> PurchaseView:
        def _op(session: Session) -> PurchaseView:
            self.authorizer.require(session, actor, "com.compras.anular")

            purchase = session.get(Purchase, purchase_id)
            if purchase is None:
                raise NotFound(f"compra {purchase_id} no existe")
            if purchase.status != "confirmada":
                raise ValidationError(
                    f"la compra {purchase.number} está '{purchase.status}': no se puede anular"
                )

            lineas = session.scalars(
                select(PurchaseLine)
                .where(PurchaseLine.purchase_id == purchase.id)
                .order_by(PurchaseLine.line_no.asc())
            ).all()
            for linea in lineas:
                self.ledger.void_reversal_of_receive(
                    session,
                    actor,
                    linea.product_id,
                    linea.qty,
                    ref_type="purchase_void",
                    ref_id=str(purchase.id),
                    reason=reason,
                )

            if purchase.credit_amount > 0:
                cuenta = session.scalar(
                    select(Account).where(
                        Account.source_type == "purchase", Account.source_id == str(purchase.id)
                    )
                )
                if cuenta is not None:
                    self.accounts.void(session, actor, cuenta.id)

            purchase.status = "anulada"
            session.flush()

            audit(
                session,
                actor,
                "com.compra.anulada",
                entity_type="com_purchase",
                entity_id=str(purchase.id),
                summary=f"Compra {purchase.number} anulada: {reason}",
                detail={"reason": reason},
                clock=self.clock,
            )

            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
            return self._to_view(session, purchase, ver_costos)

        return run_in_transaction(self.factory, _op)

    # -- Consultas ---------------------------------------------------------

    def get(self, actor: Actor, purchase_id: int) -> PurchaseView:
        def _op(session: Session) -> PurchaseView:
            self.authorizer.require(session, actor, "com.compras.ver")
            purchase = session.get(Purchase, purchase_id)
            if purchase is None:
                raise NotFound(f"compra {purchase_id} no existe")
            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")
            return self._to_view(session, purchase, ver_costos)

        return run_in_transaction(self.factory, _op, readonly=True)

    def list(
        self,
        actor: Actor,
        *,
        supplier_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        text: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> Page[PurchaseSummary]:
        def _op(session: Session) -> Page[PurchaseSummary]:
            self.authorizer.require(session, actor, "com.compras.ver")
            page_num, size, offset = normalize_page(page, page_size)

            condiciones = []
            if supplier_id is not None:
                condiciones.append(Purchase.supplier_id == supplier_id)
            if since is not None:
                condiciones.append(Purchase.purchased_at >= since)
            if until is not None:
                condiciones.append(Purchase.purchased_at <= until)

            stmt = select(Purchase, Party).join(Party, Purchase.supplier_id == Party.id)
            if condiciones:
                stmt = stmt.where(and_(*condiciones))

            texto = text.strip()
            if texto:
                texto_normalizado = normalize_search(texto)
                stmt = stmt.where(
                    Purchase.number.like(f"%{escape_like(texto)}%", escape=LIKE_ESCAPE)
                    | Party.name_search.like(
                        f"%{escape_like(texto_normalizado)}%", escape=LIKE_ESCAPE
                    )
                )

            filas = session.execute(stmt).all()
            resumenes = [self._to_summary(purchase, party) for purchase, party in filas]
            resumenes.sort(key=lambda r: (r.purchased_at, r.id), reverse=True)

            total = len(resumenes)
            pagina = resumenes[offset : offset + size]
            return Page(items=pagina, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def supplier_history(
        self, actor: Actor, supplier_id: int, page: int = 1, page_size: int = 50
    ) -> Page[PurchaseSummary]:
        return self.list(actor, supplier_id=supplier_id, page=page, page_size=page_size)

    def last_prices(
        self, actor: Actor, product_id: int, limit: int = 10
    ) -> list[SupplierPriceView]:
        def _op(session: Session) -> list[SupplierPriceView]:
            self.authorizer.require(session, actor, "com.costos.ver")
            filas = session.scalars(
                select(SupplierPrice)
                .where(SupplierPrice.product_id == product_id)
                .order_by(SupplierPrice.recorded_at.desc(), SupplierPrice.id.desc())
                .limit(limit)
            ).all()
            return [
                SupplierPriceView(
                    product_id=fila.product_id,
                    unit_cost=fila.unit_cost,
                    purchase_id=fila.purchase_id,
                    recorded_at=fila.recorded_at,
                )
                for fila in filas
            ]

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos ---------------------------------------------------------

    def _to_summary(self, purchase: Purchase, party: Party) -> PurchaseSummary:
        return PurchaseSummary(
            id=purchase.id,
            number=purchase.number,
            supplier_id=purchase.supplier_id,
            supplier_name=party.name,
            purchased_at=purchase.purchased_at,
            total=purchase.total,
            status=purchase.status,
        )

    def _to_view(self, session: Session, purchase: Purchase, ver_costos: bool) -> PurchaseView:
        lineas = session.scalars(
            select(PurchaseLine)
            .where(PurchaseLine.purchase_id == purchase.id)
            .order_by(PurchaseLine.line_no.asc())
        ).all()
        pagos = session.scalars(
            select(PurchasePayment)
            .where(PurchasePayment.purchase_id == purchase.id)
            .order_by(PurchasePayment.id.asc())
        ).all()

        lines = tuple(
            PurchaseLineView(
                line_no=linea.line_no,
                product_id=linea.product_id,
                description_snapshot=linea.description_snapshot,
                qty=linea.qty,
                unit_cost=linea.unit_cost if ver_costos else None,
                tax_rate=linea.tax_rate,
                line_subtotal=linea.line_subtotal,
                line_tax=linea.line_tax,
                line_total=linea.line_total,
                presentation=(
                    PresentationSnapshot.model_validate_json(
                        linea.presentation_snapshot
                    ).model_copy(update={"unit_amount": None})
                    if linea.presentation_snapshot and not ver_costos
                    else PresentationSnapshot.model_validate_json(linea.presentation_snapshot)
                    if linea.presentation_snapshot
                    else None
                ),
            )
            for linea in lineas
        )
        payments = tuple(
            PurchasePaymentView(method=pago.method, amount=pago.amount, reference=pago.reference)
            for pago in pagos
        )

        return PurchaseView(
            id=purchase.id,
            uuid=purchase.uuid,
            number=purchase.number,
            supplier_id=purchase.supplier_id,
            supplier_invoice_ref=purchase.supplier_invoice_ref,
            purchased_at=purchase.purchased_at,
            subtotal=purchase.subtotal,
            tax_total=purchase.tax_total,
            total=purchase.total,
            paid_initial=purchase.paid_initial,
            credit_amount=purchase.credit_amount,
            status=purchase.status,
            notes=purchase.notes,
            created_at=purchase.created_at,
            lines=lines,
            payments=payments,
        )
