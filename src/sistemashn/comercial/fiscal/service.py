"""Servicio de facturación fiscal (CAI), plan T4.5.

Deshabilitado por defecto (`core_business.fiscal_enabled = False`): ver decisiones de la Fase 4
y `docs/investigacion-facturacion-honduras.md`. Nunca se permite emitir fuera de vigencia o rango,
ni siquiera con permiso de administrador.

`FiscalService` lee `core_business` directamente con `session.get(Business, 1)` dentro de su
propia transacción, en vez de recibir `SettingsService` como dependencia: evita acoplar el
servicio fiscal a otro servicio solo para leer un booleano, y mantiene la lectura dentro de la
misma transacción atómica de la emisión.
"""

import json
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.fiscal.errors import (
    AlreadyInvoiced,
    AuthorizationExhausted,
    AuthorizationExpired,
    FiscalDisabled,
    NoActiveAuthorization,
)
from sistemashn.comercial.fiscal.models import FiscalAuthorization, FiscalInvoice
from sistemashn.comercial.fiscal.schemas import (
    FiscalAuthorizationInput,
    FiscalAuthorizationView,
    FiscalInvoiceView,
)
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound
from sistemashn.core.settings.models import Business

_DOCUMENT_TYPE_FACTURA = "factura"


def _prefijo_y_correlativo(rango: str) -> tuple[str, int]:
    prefijo, correlativo = rango.rsplit("-", 1)
    return prefijo, int(correlativo)


class FiscalService:
    """Registro de autorizaciones CAI y emisión de facturas fiscales (opcional, T4.5)."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime],
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    # -- Autorizaciones ---------------------------------------------------------

    def register_authorization(self, actor: Actor, data: FiscalAuthorizationInput) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "com.fiscal.gestionar")

            _, correlativo_inicial = _prefijo_y_correlativo(data.range_start)

            authorization = FiscalAuthorization(
                cai=data.cai,
                document_type=_DOCUMENT_TYPE_FACTURA,
                range_start=data.range_start,
                range_end=data.range_end,
                valid_until=data.valid_until,
                next_correlative=correlativo_inicial,
                status="activa",
            )
            session.add(authorization)
            session.flush()

            audit(
                session,
                actor,
                "com.fiscal.autorizacion_registrada",
                entity_type="com_fiscal_authorization",
                entity_id=str(authorization.id),
                summary=f"Autorización CAI {data.cai} registrada",
                detail={
                    "cai": data.cai,
                    "range_start": data.range_start,
                    "range_end": data.range_end,
                },
                clock=self.clock,
            )

            return authorization.id

        return run_in_transaction(self.factory, _op)

    def list_authorizations(self, actor: Actor) -> list[FiscalAuthorizationView]:
        def _op(session: Session) -> list[FiscalAuthorizationView]:
            self.authorizer.require(session, actor, "com.fiscal.gestionar")
            filas = session.scalars(
                select(FiscalAuthorization).order_by(FiscalAuthorization.id.asc())
            ).all()
            return [self._authorization_to_view(fila) for fila in filas]

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Emisión ---------------------------------------------------------

    def _sync_authorization_statuses(self) -> None:
        """Marca perezosamente 'vencida'/'agotada' las autorizaciones 'activa' que ya no
        sirven, en su propia transacción que siempre confirma (no depende de que la operación
        que la disparó también tenga éxito, ya que un rollback por otra causa no debe deshacer
        este marcado)."""

        def _op(session: Session) -> None:
            hoy = self.clock().date()
            filas = session.scalars(
                select(FiscalAuthorization).where(FiscalAuthorization.status == "activa")
            ).all()
            for fila in filas:
                _, correlativo_final = _prefijo_y_correlativo(fila.range_end)
                if fila.next_correlative > correlativo_final:
                    fila.status = "agotada"
                elif hoy > fila.valid_until:
                    fila.status = "vencida"
            session.flush()

        run_in_transaction(self.factory, _op)

    def issue(self, actor: Actor, sale_id: int, snapshot: dict) -> FiscalInvoiceView:
        self._sync_authorization_statuses()

        def _op(session: Session) -> FiscalInvoiceView:
            self.authorizer.require(session, actor, "com.fiscal.gestionar")

            business = session.get(Business, 1)
            if business is None or not business.fiscal_enabled:
                raise FiscalDisabled("la facturación fiscal no está habilitada para este negocio")

            authorization = session.scalars(
                select(FiscalAuthorization)
                .where(
                    FiscalAuthorization.document_type == _DOCUMENT_TYPE_FACTURA,
                    FiscalAuthorization.status == "activa",
                )
                .order_by(FiscalAuthorization.id.asc())
            ).first()
            if authorization is None:
                # Ninguna autorización sirve ya: se distingue el motivo con la más reciente
                # registrada para el tipo de documento, si existe, para dar un mensaje claro.
                cualquiera = session.scalars(
                    select(FiscalAuthorization)
                    .where(FiscalAuthorization.document_type == _DOCUMENT_TYPE_FACTURA)
                    .order_by(FiscalAuthorization.id.desc())
                ).first()
                if cualquiera is not None and cualquiera.status == "vencida":
                    raise AuthorizationExpired(
                        f"la autorización CAI {cualquiera.cai} venció el {cualquiera.valid_until}"
                    )
                if cualquiera is not None and cualquiera.status == "agotada":
                    raise AuthorizationExhausted(
                        f"la autorización CAI {cualquiera.cai} agotó su rango de correlativos"
                    )
                raise NoActiveAuthorization("no hay ninguna autorización CAI activa para facturas")

            _, correlativo_final = _prefijo_y_correlativo(authorization.range_end)

            ya_emitida = session.scalar(
                select(FiscalInvoice).where(FiscalInvoice.sale_id == sale_id)
            )
            if ya_emitida is not None:
                raise AlreadyInvoiced(f"la venta {sale_id} ya tiene una factura fiscal emitida")

            prefijo, _ = _prefijo_y_correlativo(authorization.range_start)
            numero_fiscal = f"{prefijo}-{authorization.next_correlative:08d}"
            ahora = self.clock()

            invoice = FiscalInvoice(
                sale_id=sale_id,
                authorization_id=authorization.id,
                fiscal_number=numero_fiscal,
                issued_at=ahora,
                snapshot_json=json.dumps(snapshot, default=str),
            )
            session.add(invoice)

            authorization.next_correlative += 1
            if authorization.next_correlative > correlativo_final:
                authorization.status = "agotada"
            session.flush()

            audit(
                session,
                actor,
                "com.factura_fiscal.emitida",
                entity_type="com_fiscal_invoice",
                entity_id=str(invoice.id),
                summary=f"Factura fiscal {numero_fiscal} emitida para la venta {sale_id}",
                detail={"sale_id": sale_id, "fiscal_number": numero_fiscal},
                clock=self.clock,
            )

            return self._invoice_to_view(invoice)

        return run_in_transaction(self.factory, _op)

    # -- Consultas ---------------------------------------------------------

    def get(self, actor: Actor, invoice_id: int) -> FiscalInvoiceView:
        def _op(session: Session) -> FiscalInvoiceView:
            self.authorizer.require(session, actor, "com.fiscal.gestionar")
            invoice = session.get(FiscalInvoice, invoice_id)
            if invoice is None:
                raise NotFound(f"factura fiscal {invoice_id} no existe")
            return self._invoice_to_view(invoice)

        return run_in_transaction(self.factory, _op, readonly=True)

    def get_by_sale(self, actor: Actor, sale_id: int) -> FiscalInvoiceView | None:
        def _op(session: Session) -> FiscalInvoiceView | None:
            self.authorizer.require(session, actor, "com.fiscal.gestionar")
            invoice = session.scalar(select(FiscalInvoice).where(FiscalInvoice.sale_id == sale_id))
            if invoice is None:
                return None
            return self._invoice_to_view(invoice)

        return run_in_transaction(self.factory, _op, readonly=True)

    def is_available(self, actor: Actor) -> bool:
        """Informa si la UI puede ofrecer "Emitir factura fiscal": no requiere permiso propio
        porque solo expone un booleano (ni datos del CAI ni de la venta)."""
        self._sync_authorization_statuses()

        def _op(session: Session) -> bool:
            business = session.get(Business, 1)
            if business is None or not business.fiscal_enabled:
                return False

            authorization = session.scalar(
                select(FiscalAuthorization).where(
                    FiscalAuthorization.document_type == _DOCUMENT_TYPE_FACTURA,
                    FiscalAuthorization.status == "activa",
                )
            )
            return authorization is not None

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos ---------------------------------------------------------

    def _authorization_to_view(self, fila: FiscalAuthorization) -> FiscalAuthorizationView:
        return FiscalAuthorizationView(
            id=fila.id,
            cai=fila.cai,
            document_type=fila.document_type,
            range_start=fila.range_start,
            range_end=fila.range_end,
            valid_until=fila.valid_until,
            next_correlative=fila.next_correlative,
            status=fila.status,
        )

    def _invoice_to_view(self, invoice: FiscalInvoice) -> FiscalInvoiceView:
        return FiscalInvoiceView(
            id=invoice.id,
            sale_id=invoice.sale_id,
            authorization_id=invoice.authorization_id,
            fiscal_number=invoice.fiscal_number,
            issued_at=invoice.issued_at,
        )
