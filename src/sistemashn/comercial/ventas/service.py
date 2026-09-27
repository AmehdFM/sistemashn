"""Servicio de ventas: confirmación, conversión de cotización y consultas (plan T4.2)."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.caja.service import CashService
from sistemashn.comercial.catalogo import kits
from sistemashn.comercial.catalogo.models import Product
from sistemashn.comercial.cotizaciones.models import Quote, QuoteLine
from sistemashn.comercial.cotizaciones.service import QuoteService
from sistemashn.comercial.credito.models import Account
from sistemashn.comercial.credito.schemas import AccountKind
from sistemashn.comercial.credito.service import AccountService
from sistemashn.comercial.fiscal.service import FiscalService
from sistemashn.comercial.idempotency import find_previous, remember
from sistemashn.comercial.inventario.errors import InsufficientStock
from sistemashn.comercial.inventario.ledger import InventoryLedger
from sistemashn.comercial.inventario.models import Stock
from sistemashn.comercial.pagos.methods import PaymentMethod
from sistemashn.comercial.sequences import format_number, next_number
from sistemashn.comercial.ventas.errors import (
    InvalidSaleLine,
    PaymentsMismatch,
    PriceOrStockDifference,
    QuoteConversionMismatch,
)
from sistemashn.comercial.ventas.models import Sale, SaleLine, SalePayment
from sistemashn.comercial.ventas.schemas import (
    SaleInput,
    SaleLineView,
    SalePaymentView,
    SaleSummary,
    SaleView,
)
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.money import money
from sistemashn.core.money import unit_cost as quantize_unit_cost
from sistemashn.core.pagination import Page, normalize_page

_OPERATION = "venta.confirmar"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SaleService:
    """Confirmación de ventas (con o sin conversión de cotización), consultas e historial."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime],
        ledger: InventoryLedger,
        accounts: AccountService,
        cash: CashService,
        quotes: QuoteService,
        fiscal: FiscalService | None = None,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.ledger = ledger
        self.accounts = accounts
        self.cash = cash
        self.quotes = quotes
        # Opcional: si no se pasa (p. ej. en pruebas que no lo necesitan), `void` omite la
        # validación de factura fiscal emitida en vez de fallar por dependencia faltante.
        self.fiscal = fiscal

    # -- Confirmación ---------------------------------------------------------

    def confirm(self, actor: Actor, data: SaleInput) -> SaleView:
        def _op(session: Session) -> SaleView:
            self.authorizer.require(session, actor, "com.ventas.registrar")

            previo = find_previous(session, data.request_id, _OPERATION)
            if previo is not None:
                sale = session.get(Sale, int(previo))
                if sale is None:
                    raise NotFound(f"venta {previo} no existe")
                return self._to_view(session, sale)

            quote: Quote | None = None
            usa_apartado = False
            if data.quote_id is not None:
                quote = session.get(Quote, data.quote_id)
                if quote is None:
                    raise ValidationError(f"cotización {data.quote_id} no existe")
                # Simplificación T4.2: el vencimiento perezoso completo de `QuoteService` no se
                # reutiliza dentro de esta misma transacción (evita anidar transacciones); basta
                # con rechazar la conversión si la cotización ya no está abierta.
                if quote.status != "abierta":
                    raise ValidationError(
                        f"la cotización {quote.number} está '{quote.status}': no se puede convertir"
                    )
                usa_apartado = quote.has_reservation

                diferencias = self._revalidar_cotizacion(session, quote)
                if diferencias and not data.accept_changes:
                    raise QuoteConversionMismatch(diferencias)

            # -- Validación y cálculo de TODAS las líneas antes de mutar cualquier estado ------
            lineas_calculadas: list[dict] = []
            demanda: dict[int, Decimal] = {}
            for indice, linea in enumerate(data.lines, start=1):
                product = session.get(Product, linea.product_id)
                if product is None:
                    raise InvalidSaleLine(f"producto {linea.product_id} no existe")
                if not product.active:
                    raise InvalidSaleLine(f"el producto '{product.code}' está inactivo")

                precio = linea.unit_price if linea.unit_price is not None else product.sale_price
                tasa = linea.tax_rate if linea.tax_rate is not None else product.tax_rate
                subtotal = money(linea.qty * precio)
                impuesto = money(subtotal * tasa)
                total_linea = money(subtotal + impuesto)

                kit_lines = None
                if product.is_kit:
                    kit_lines = kits.explode(session, product.id, linea.qty)
                    for kl in kit_lines:
                        demanda[kl.component_id] = (
                            demanda.get(kl.component_id, Decimal("0")) + kl.qty
                        )
                else:
                    demanda[product.id] = demanda.get(product.id, Decimal("0")) + linea.qty

                lineas_calculadas.append(
                    {
                        "line_no": indice,
                        "product": product,
                        "qty": linea.qty,
                        "unit_price": precio,
                        "tax_rate": tasa,
                        "subtotal": subtotal,
                        "tax": impuesto,
                        "total": total_linea,
                        "kit_lines": kit_lines,
                    }
                )

            # Se verifica disponibilidad agregada de cada componente ANTES de mover inventario:
            # si algún producto no alcanza, no debe quedar rastro de ninguna línea.
            for product_id, cantidad in demanda.items():
                self._verificar_disponibilidad(session, product_id, cantidad, usa_apartado)

            subtotal_venta = money(sum((li["subtotal"] for li in lineas_calculadas), Decimal("0")))
            tax_total = money(sum((li["tax"] for li in lineas_calculadas), Decimal("0")))
            total_venta = money(subtotal_venta + tax_total)

            pagado, vuelto, credito = self._calcular_pagos(data, total_venta)

            if credito > 0 and data.customer_id is None:
                raise ValidationError("una venta a crédito requiere un cliente")
            if credito > 0 and data.credit_due_date is None:
                raise ValidationError("una venta a crédito requiere fecha de vencimiento")

            numero = format_number("V", next_number(session, "venta"))
            ahora = self.clock()

            sale = Sale(
                uuid=uuid4().hex,
                number=numero,
                quote_id=data.quote_id,
                customer_id=data.customer_id,
                sold_at=ahora,
                subtotal=subtotal_venta,
                tax_total=tax_total,
                total=total_venta,
                paid_amount=pagado,
                change_amount=vuelto,
                credit_amount=credito,
                status="confirmada",
                user_id=actor.user_id,
                cash_session_id=data.cash_session_id,
                notes=data.notes,
                created_at=ahora,
            )
            session.add(sale)
            session.flush()

            for li in lineas_calculadas:
                product = li["product"]
                kit_lines = li["kit_lines"]
                session.add(
                    SaleLine(
                        sale_id=sale.id,
                        line_no=li["line_no"],
                        product_id=product.id,
                        description_snapshot=product.name,
                        qty=li["qty"],
                        unit_price=li["unit_price"],
                        tax_rate=li["tax_rate"],
                        line_subtotal=li["subtotal"],
                        line_tax=li["tax"],
                        line_total=li["total"],
                        unit_cost_snapshot=self._costo_kit(kit_lines, li["qty"])
                        if kit_lines is not None
                        else self._emitir(
                            session, actor, product.id, li["qty"], usa_apartado, sale.id
                        ),
                        kit_component_of=None,
                    )
                )
                if kit_lines is not None:
                    for kl in kit_lines:
                        costo_componente = self._emitir(
                            session, actor, kl.component_id, kl.qty, usa_apartado, sale.id
                        )
                        session.add(
                            SaleLine(
                                sale_id=sale.id,
                                line_no=li["line_no"],
                                product_id=kl.component_id,
                                description_snapshot=self._nombre_producto(
                                    session, kl.component_id
                                ),
                                qty=kl.qty,
                                unit_price=Decimal("0.00"),
                                tax_rate=Decimal("0.0000"),
                                line_subtotal=Decimal("0.00"),
                                line_tax=Decimal("0.00"),
                                line_total=Decimal("0.00"),
                                unit_cost_snapshot=costo_componente,
                                kit_component_of=li["line_no"],
                            )
                        )

            for pago in data.payments:
                session.add(
                    SalePayment(
                        sale_id=sale.id,
                        method=pago.method.value,
                        amount=pago.amount,
                        reference=pago.reference,
                    )
                )
            session.flush()

            efectivo = money(
                sum(
                    (p.amount for p in data.payments if p.method == PaymentMethod.EFECTIVO),
                    Decimal("0"),
                )
            )
            if efectivo > 0 and data.cash_session_id is not None:
                # Simplificación T4.2: si hay efectivo pero no se indicó `cash_session_id`, la
                # venta no falla por eso (la política estricta de "requiere caja abierta" queda
                # para quien conecte la UI en T4.6).
                self.cash.register_entry(
                    session,
                    actor,
                    data.cash_session_id,
                    efectivo,
                    kind="venta",
                    ref_type="sale",
                    ref_id=str(sale.id),
                )

            if credito > 0:
                self.accounts.create_account(
                    session,
                    actor,
                    kind=AccountKind.RECEIVABLE,
                    party_id=data.customer_id,  # type: ignore[arg-type]
                    source_type="sale",
                    source_id=str(sale.id),
                    amount=credito,
                    due_date=data.credit_due_date,  # type: ignore[arg-type]
                )

            if quote is not None:
                quote.status = "convertida"

            remember(session, data.request_id, _OPERATION, str(sale.id), self.clock)

            audit(
                session,
                actor,
                "com.venta.confirmada",
                entity_type="com_sale",
                entity_id=str(sale.id),
                summary=f"Venta {numero} confirmada por {total_venta}",
                detail={
                    "number": numero,
                    "customer_id": data.customer_id,
                    "quote_id": data.quote_id,
                    "subtotal": subtotal_venta,
                    "tax_total": tax_total,
                    "total": total_venta,
                    "paid_amount": pagado,
                    "change_amount": vuelto,
                    "credit_amount": credito,
                },
                clock=self.clock,
            )

            return self._to_view(session, sale)

        return run_in_transaction(self.factory, _op)

    # -- Anulación ---------------------------------------------------------

    def void(self, actor: Actor, sale_id: int, reason: str) -> SaleView:
        def _op(session: Session) -> SaleView:
            self.authorizer.require(session, actor, "com.ventas.anular")

            sale = session.get(Sale, sale_id)
            if sale is None:
                raise NotFound(f"venta {sale_id} no existe")
            if sale.status != "confirmada":
                raise ValidationError(
                    f"la venta {sale.number} está '{sale.status}': no se puede anular"
                )

            if self.fiscal is not None:
                factura = self.fiscal.get_by_sale(actor, sale_id)
                if factura is not None:
                    raise ValidationError(
                        "no se puede anular: la venta tiene una factura fiscal emitida "
                        "(requiere nota de crédito, fuera de alcance)"
                    )

            lineas = session.scalars(
                select(SaleLine).where(SaleLine.sale_id == sale.id).order_by(SaleLine.id.asc())
            ).all()
            pagos = session.scalars(select(SalePayment).where(SalePayment.sale_id == sale.id)).all()

            # Se valida la caja ANTES de tocar inventario o cuentas: si la sesión donde se
            # cobró ya cerró, la anulación se rechaza sin dejar ningún rastro parcial.
            efectivo = money(
                sum(
                    (p.amount for p in pagos if p.method == PaymentMethod.EFECTIVO.value),
                    Decimal("0"),
                )
            )
            if efectivo > 0 and sale.cash_session_id is not None:
                self.cash.reverse_entry(
                    session,
                    actor,
                    sale.cash_session_id,
                    efectivo,
                    ref_type="sale_void",
                    ref_id=str(sale.id),
                )

            for linea in lineas:
                product = session.get(Product, linea.product_id)
                if product is not None and product.is_kit:
                    # La línea del kit en sí no tiene existencias propias: solo sus componentes
                    # (líneas con `kit_component_of` apuntando a esta) revierten inventario.
                    continue
                self.ledger.void_reversal_of_issue(
                    session,
                    actor,
                    linea.product_id,
                    linea.qty,
                    linea.unit_cost_snapshot,
                    ref_type="sale_void",
                    ref_id=str(sale.id),
                    reason=reason,
                )

            if sale.credit_amount > 0:
                cuenta = session.scalar(
                    select(Account).where(
                        Account.source_type == "sale", Account.source_id == str(sale.id)
                    )
                )
                if cuenta is not None:
                    self.accounts.void(session, actor, cuenta.id)

            sale.status = "anulada"
            session.flush()

            audit(
                session,
                actor,
                "com.venta.anulada",
                entity_type="com_sale",
                entity_id=str(sale.id),
                summary=f"Venta {sale.number} anulada: {reason}",
                detail={"reason": reason},
                clock=self.clock,
            )

            return self._to_view(session, sale)

        return run_in_transaction(self.factory, _op)

    # -- Internos: pagos ---------------------------------------------------------

    def _calcular_pagos(self, data: SaleInput, total: Decimal) -> tuple[Decimal, Decimal, Decimal]:
        pagado = money(sum((p.amount for p in data.payments), Decimal("0")))
        efectivo = money(
            sum(
                (p.amount for p in data.payments if p.method == PaymentMethod.EFECTIVO),
                Decimal("0"),
            )
        )
        if pagado > total:
            exceso = money(pagado - total)
            if efectivo <= 0:
                raise PaymentsMismatch(
                    "los pagos exceden el total de la venta sin efectivo con qué dar vuelto"
                )
            vuelto = min(exceso, efectivo)
            credito = Decimal("0.00")
        else:
            vuelto = Decimal("0.00")
            credito = money(total - pagado)
        return pagado, vuelto, credito

    # -- Internos: inventario ---------------------------------------------------------

    def _verificar_disponibilidad(
        self, session: Session, product_id: int, cantidad: Decimal, usa_apartado: bool
    ) -> None:
        stock = session.get(Stock, product_id)
        if stock is None:
            raise NotFound(f"el producto {product_id} no tiene existencias")
        disponible = stock.reserved if usa_apartado else stock.on_hand - stock.reserved
        if cantidad > disponible:
            raise InsufficientStock(product_id, disponible, cantidad)

    def _emitir(
        self,
        session: Session,
        actor: Actor,
        product_id: int,
        cantidad: Decimal,
        usa_apartado: bool,
        sale_id: int,
    ) -> Decimal:
        if usa_apartado:
            return self.ledger.issue_reserved(
                session, actor, product_id, cantidad, ref_type="sale", ref_id=str(sale_id)
            )
        return self.ledger.issue(
            session, actor, product_id, cantidad, ref_type="sale", ref_id=str(sale_id)
        )

    def _costo_kit(self, kit_lines: list[kits.KitLine], qty_kit: Decimal) -> Decimal:
        total_costo = sum((kl.qty * kl.avg_cost for kl in kit_lines), Decimal("0"))
        if qty_kit == 0:
            return Decimal("0.0000")
        return quantize_unit_cost(total_costo / qty_kit)

    def _nombre_producto(self, session: Session, product_id: int) -> str:
        product = session.get(Product, product_id)
        return product.name if product is not None else ""

    # -- Internos: conversión de cotización ---------------------------------------------------

    def _revalidar_cotizacion(self, session: Session, quote: Quote) -> list[PriceOrStockDifference]:
        diferencias: list[PriceOrStockDifference] = []
        lineas = session.scalars(select(QuoteLine).where(QuoteLine.quote_id == quote.id)).all()
        for linea in lineas:
            product = session.get(Product, linea.product_id)
            if product is None:
                continue
            if product.sale_price != linea.unit_price:
                diferencias.append(
                    PriceOrStockDifference(
                        product_id=product.id,
                        field="unit_price",
                        expected=linea.unit_price,
                        actual=product.sale_price,
                    )
                )
            if not quote.has_reservation:
                if product.is_kit:
                    disponible = kits.availability(session, product.id)
                else:
                    stock = session.get(Stock, product.id)
                    disponible = (
                        stock.on_hand - stock.reserved if stock is not None else Decimal("0")
                    )
                if disponible < linea.qty:
                    diferencias.append(
                        PriceOrStockDifference(
                            product_id=product.id,
                            field="qty_disponible",
                            expected=linea.qty,
                            actual=disponible,
                        )
                    )
        return diferencias

    # -- Consultas ---------------------------------------------------------

    def get(self, actor: Actor, sale_id: int) -> SaleView:
        def _op(session: Session) -> SaleView:
            self.authorizer.require(session, actor, "com.ventas.ver")
            sale = session.get(Sale, sale_id)
            if sale is None:
                raise NotFound(f"venta {sale_id} no existe")
            return self._to_view(session, sale)

        return run_in_transaction(self.factory, _op, readonly=True)

    def list(
        self,
        actor: Actor,
        *,
        customer_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        text: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> Page[SaleSummary]:
        def _op(session: Session) -> Page[SaleSummary]:
            self.authorizer.require(session, actor, "com.ventas.ver")
            page_num, size, offset = normalize_page(page, page_size)

            condiciones = []
            if customer_id is not None:
                condiciones.append(Sale.customer_id == customer_id)
            if since is not None:
                condiciones.append(Sale.sold_at >= since)
            if until is not None:
                condiciones.append(Sale.sold_at <= until)

            stmt = select(Sale)
            if condiciones:
                stmt = stmt.where(and_(*condiciones))

            texto = text.strip()
            if texto:
                stmt = stmt.where(Sale.number.like(f"%{texto}%"))

            ventas = session.scalars(stmt).all()
            resumenes = [self._to_summary(v) for v in ventas]
            resumenes.sort(key=lambda r: (r.sold_at, r.id), reverse=True)

            total = len(resumenes)
            pagina = resumenes[offset : offset + size]
            return Page(items=pagina, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    def history(
        self, actor: Actor, customer_id: int, page: int = 1, page_size: int = 50
    ) -> Page[SaleSummary]:
        return self.list(actor, customer_id=customer_id, page=page, page_size=page_size)

    # -- Internos: vistas ---------------------------------------------------------

    def _to_summary(self, sale: Sale) -> SaleSummary:
        return SaleSummary(
            id=sale.id,
            number=sale.number,
            customer_id=sale.customer_id,
            sold_at=sale.sold_at,
            total=sale.total,
            status=sale.status,
        )

    def _to_view(self, session: Session, sale: Sale) -> SaleView:
        lineas = session.scalars(
            select(SaleLine).where(SaleLine.sale_id == sale.id).order_by(SaleLine.id.asc())
        ).all()
        pagos = session.scalars(
            select(SalePayment).where(SalePayment.sale_id == sale.id).order_by(SalePayment.id.asc())
        ).all()

        lines = tuple(
            SaleLineView(
                line_no=linea.line_no,
                product_id=linea.product_id,
                description_snapshot=linea.description_snapshot,
                qty=linea.qty,
                unit_price=linea.unit_price,
                tax_rate=linea.tax_rate,
                line_subtotal=linea.line_subtotal,
                line_tax=linea.line_tax,
                line_total=linea.line_total,
                unit_cost_snapshot=linea.unit_cost_snapshot,
                kit_component_of=linea.kit_component_of,
            )
            for linea in lineas
        )
        payments = tuple(
            SalePaymentView(method=pago.method, amount=pago.amount, reference=pago.reference)
            for pago in pagos
        )

        return SaleView(
            id=sale.id,
            uuid=sale.uuid,
            number=sale.number,
            quote_id=sale.quote_id,
            customer_id=sale.customer_id,
            sold_at=sale.sold_at,
            subtotal=sale.subtotal,
            tax_total=sale.tax_total,
            total=sale.total,
            paid_amount=sale.paid_amount,
            change_amount=sale.change_amount,
            credit_amount=sale.credit_amount,
            status=sale.status,
            cash_session_id=sale.cash_session_id,
            notes=sale.notes,
            created_at=sale.created_at,
            lines=lines,
            payments=payments,
        )
