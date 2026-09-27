"""Servicio de cotizaciones: apartado de inventario y vencimiento perezoso (plan T4.1)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo import kits
from sistemashn.comercial.catalogo.models import Product
from sistemashn.comercial.cotizaciones.errors import InvalidQuoteLine, InvalidQuoteStatus
from sistemashn.comercial.cotizaciones.models import Quote, QuoteLine
from sistemashn.comercial.cotizaciones.schemas import (
    QuoteInput,
    QuoteLineView,
    QuoteSummary,
    QuoteView,
)
from sistemashn.comercial.idempotency import find_previous, remember
from sistemashn.comercial.inventario.ledger import InventoryLedger
from sistemashn.comercial.sequences import format_number, next_number
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import SYSTEM_ACTOR, Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound
from sistemashn.core.money import money
from sistemashn.core.pagination import Page, normalize_page

_OPERATION = "cotizacion.crear"

# Honduras no observa horario de verano: UTC-6 todo el año.
_HONDURAS_OFFSET = timedelta(hours=-6)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class QuoteService:
    """Alta, consulta y vencimiento perezoso de cotizaciones con apartado opcional."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime],
        ledger: InventoryLedger,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.ledger = ledger

    def _today_honduras(self):
        return (self.clock() + _HONDURAS_OFFSET).date()

    # -- Alta ---------------------------------------------------------

    def create(self, actor: Actor, data: QuoteInput) -> QuoteView:
        def _op(session: Session) -> QuoteView:
            self.authorizer.require(session, actor, "com.cotizaciones.gestionar")

            previo = find_previous(session, data.request_id, _OPERATION)
            if previo is not None:
                quote = session.get(Quote, int(previo))
                if quote is None:
                    raise NotFound(f"cotización {previo} no existe")
                self._vencer_si_corresponde(session, quote)
                return self._to_view(session, quote)

            # Se validan y calculan TODAS las líneas antes de reservar nada: si una falla, no
            # debe quedar rastro de las anteriores.
            lineas_calculadas: list[dict] = []
            for indice, linea in enumerate(data.lines, start=1):
                product = session.get(Product, linea.product_id)
                if product is None:
                    raise InvalidQuoteLine(f"producto {linea.product_id} no existe")
                if not product.active:
                    raise InvalidQuoteLine(f"el producto '{product.code}' está inactivo")

                precio = linea.unit_price if linea.unit_price is not None else product.sale_price
                tasa = linea.tax_rate if linea.tax_rate is not None else product.tax_rate
                subtotal = money(linea.qty * precio)
                impuesto = money(subtotal * tasa)
                total_linea = money(subtotal + impuesto)

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
                    }
                )

            subtotal_cot = money(sum((li["subtotal"] for li in lineas_calculadas), Decimal("0")))
            tax_total = money(sum((li["tax"] for li in lineas_calculadas), Decimal("0")))
            total_cot = money(subtotal_cot + tax_total)

            numero = format_number("Q", next_number(session, "cotizacion"))
            ahora = self.clock()

            quote = Quote(
                uuid=uuid4().hex,
                number=numero,
                customer_id=data.customer_id,
                status="abierta",
                valid_until=data.valid_until,
                has_reservation=data.reserve,
                subtotal=subtotal_cot,
                tax_total=tax_total,
                total=total_cot,
                user_id=actor.user_id,
                notes=data.notes,
                created_at=ahora,
            )
            session.add(quote)
            session.flush()

            for li in lineas_calculadas:
                product = li["product"]
                session.add(
                    QuoteLine(
                        quote_id=quote.id,
                        line_no=li["line_no"],
                        product_id=product.id,
                        description_snapshot=product.name,
                        qty=li["qty"],
                        unit_price=li["unit_price"],
                        tax_rate=li["tax_rate"],
                        line_subtotal=li["subtotal"],
                        line_tax=li["tax"],
                        line_total=li["total"],
                    )
                )

            if data.reserve:
                # Si algún componente no alcanza, `InventoryLedger.reserve`/`kits.explode`
                # levantan una excepción que propaga sin commit: `run_in_transaction` hace
                # rollback de toda la transacción, así que ninguna línea anterior queda
                # reservada.
                for li in lineas_calculadas:
                    self._reservar_linea(session, actor, quote.id, li["product"], li["qty"])

            remember(session, data.request_id, _OPERATION, str(quote.id), self.clock)

            audit(
                session,
                actor,
                "com.cotizacion.creada",
                entity_type="com_quote",
                entity_id=str(quote.id),
                summary=f"Cotización {numero} creada por {total_cot}",
                detail={
                    "number": numero,
                    "customer_id": data.customer_id,
                    "reserve": data.reserve,
                    "total": total_cot,
                },
                clock=self.clock,
            )

            return self._to_view(session, quote)

        return run_in_transaction(self.factory, _op)

    def _reservar_linea(
        self, session: Session, actor: Actor, quote_id: int, product: Product, cantidad: Decimal
    ) -> None:
        if product.is_kit:
            for componente in kits.explode(session, product.id, cantidad):
                self.ledger.reserve(
                    session,
                    actor,
                    componente.component_id,
                    componente.qty,
                    ref_type="quote",
                    ref_id=str(quote_id),
                )
        else:
            self.ledger.reserve(
                session, actor, product.id, cantidad, ref_type="quote", ref_id=str(quote_id)
            )

    def _liberar_linea(
        self, session: Session, actor: Actor, quote_id: int, product: Product, cantidad: Decimal
    ) -> None:
        if product.is_kit:
            for componente in kits.explode(session, product.id, cantidad):
                self.ledger.release(
                    session,
                    actor,
                    componente.component_id,
                    componente.qty,
                    ref_type="quote",
                    ref_id=str(quote_id),
                )
        else:
            self.ledger.release(
                session, actor, product.id, cantidad, ref_type="quote", ref_id=str(quote_id)
            )

    # -- Vencimiento perezoso ---------------------------------------------

    def _vencer_si_corresponde(self, session: Session, quote: Quote) -> None:
        """Si la cotización ya venció, libera sus reservas y la marca `vencida`.

        Es idempotente: llamarla dos veces sobre una cotización ya vencida no libera reservas
        de nuevo (solo actúa mientras `status == 'abierta'`).
        """
        if quote.status != "abierta":
            return
        if self._today_honduras() <= quote.valid_until:
            return

        # El actor real que dispara la consulta no siempre tiene permiso para mover inventario
        # (p. ej. `com.cotizaciones.ver` no implica `com.inventario.ajustar`); el vencimiento es
        # un evento del sistema, se audita y libera con el actor de sistema.
        actor_sistema = SYSTEM_ACTOR

        if quote.has_reservation:
            lineas = session.scalars(select(QuoteLine).where(QuoteLine.quote_id == quote.id)).all()
            for linea in lineas:
                product = session.get(Product, linea.product_id)
                if product is None:
                    continue
                self._liberar_linea(session, actor_sistema, quote.id, product, linea.qty)

        quote.status = "vencida"

        audit(
            session,
            actor_sistema,
            "com.cotizacion.vencida",
            entity_type="com_quote",
            entity_id=str(quote.id),
            summary=f"Cotización {quote.number} vencida",
            detail={"valid_until": quote.valid_until},
            clock=self.clock,
        )

    # -- Consultas y operaciones ---------------------------------------------

    def get(self, actor: Actor, quote_id: int) -> QuoteView:
        def _op(session: Session) -> QuoteView:
            self.authorizer.require(session, actor, "com.cotizaciones.ver")
            quote = session.get(Quote, quote_id)
            if quote is None:
                raise NotFound(f"cotización {quote_id} no existe")
            self._vencer_si_corresponde(session, quote)
            return self._to_view(session, quote)

        return run_in_transaction(self.factory, _op)

    def cancel(self, actor: Actor, quote_id: int) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.cotizaciones.gestionar")
            quote = session.get(Quote, quote_id)
            if quote is None:
                raise NotFound(f"cotización {quote_id} no existe")

            self._vencer_si_corresponde(session, quote)

            if quote.status != "abierta":
                raise InvalidQuoteStatus(
                    f"la cotización {quote.number} está '{quote.status}': no se puede cancelar"
                )

            if quote.has_reservation:
                lineas = session.scalars(
                    select(QuoteLine).where(QuoteLine.quote_id == quote.id)
                ).all()
                for linea in lineas:
                    product = session.get(Product, linea.product_id)
                    if product is None:
                        continue
                    self._liberar_linea(session, actor, quote.id, product, linea.qty)

            quote.status = "cancelada"

            audit(
                session,
                actor,
                "com.cotizacion.cancelada",
                entity_type="com_quote",
                entity_id=str(quote.id),
                summary=f"Cotización {quote.number} cancelada",
                detail={},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def list(
        self,
        actor: Actor,
        *,
        status: str | None = None,
        customer_id: int | None = None,
        text: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> Page[QuoteSummary]:
        def _op(session: Session) -> Page[QuoteSummary]:
            self.authorizer.require(session, actor, "com.cotizaciones.ver")
            page_num, size, offset = normalize_page(page, page_size)

            stmt = select(Quote)
            if customer_id is not None:
                stmt = stmt.where(Quote.customer_id == customer_id)

            texto = text.strip()
            if texto:
                stmt = stmt.where(Quote.number.like(f"%{texto}%"))

            quotes = session.scalars(stmt).all()

            # Lectura, sin escritura de estado: el vencimiento perezoso se refleja al hacer
            # `get`/`cancel` de una cotización en particular, no en este listado (evita convertir
            # una consulta de lectura en una transacción de escritura solo por listar). Aquí se
            # calcula el estado "en vivo" únicamente para mostrarlo en el resumen, sin persistirlo.
            resumenes = [self._to_summary_lazy(q) for q in quotes]
            if status is not None:
                resumenes = [r for r in resumenes if r.status == status]

            resumenes.sort(key=lambda r: (r.created_at, r.id), reverse=True)
            total = len(resumenes)
            pagina = resumenes[offset : offset + size]
            return Page(items=pagina, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos ---------------------------------------------------------

    def _estado_en_vivo(self, quote: Quote) -> str:
        if quote.status == "abierta" and self._today_honduras() > quote.valid_until:
            return "vencida"
        return quote.status

    def _to_summary_lazy(self, quote: Quote) -> QuoteSummary:
        return QuoteSummary(
            id=quote.id,
            number=quote.number,
            customer_id=quote.customer_id,
            status=self._estado_en_vivo(quote),
            valid_until=quote.valid_until,
            total=quote.total,
            created_at=quote.created_at,
        )

    def _to_view(self, session: Session, quote: Quote) -> QuoteView:
        lineas = session.scalars(
            select(QuoteLine)
            .where(QuoteLine.quote_id == quote.id)
            .order_by(QuoteLine.line_no.asc())
        ).all()
        lines = tuple(
            QuoteLineView(
                line_no=linea.line_no,
                product_id=linea.product_id,
                description_snapshot=linea.description_snapshot,
                qty=linea.qty,
                unit_price=linea.unit_price,
                tax_rate=linea.tax_rate,
                line_subtotal=linea.line_subtotal,
                line_tax=linea.line_tax,
                line_total=linea.line_total,
            )
            for linea in lineas
        )
        return QuoteView(
            id=quote.id,
            uuid=quote.uuid,
            number=quote.number,
            customer_id=quote.customer_id,
            status=quote.status,
            valid_until=quote.valid_until,
            has_reservation=quote.has_reservation,
            subtotal=quote.subtotal,
            tax_total=quote.tax_total,
            total=quote.total,
            notes=quote.notes,
            created_at=quote.created_at,
            lines=lines,
        )
