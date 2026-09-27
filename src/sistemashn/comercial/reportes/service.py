"""Servicio de reportes: consultas de solo lectura sobre tablas ya existentes (plan T5.5).

`ReportService` no declara modelos ni tablas propias: lee directamente `com_sale`/
`com_sale_line`/`com_purchase`/`com_account`/`com_cash_session` con SQLAlchemy. La utilidad de
`sales_and_profit` usa siempre el costo histórico congelado en `com_sale_line.unit_cost_snapshot`,
nunca el costo promedio actual del producto (que puede haber cambiado por compras posteriores).
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.caja.models import CashSession
from sistemashn.comercial.contrapartes.models import Party
from sistemashn.comercial.credito.models import Account
from sistemashn.comercial.inventario.service import InventoryService
from sistemashn.comercial.reportes.schemas import (
    AccountBalanceRow,
    CashClosureRow,
    LowStockRow,
    SalesProfitReport,
    SalesProfitRow,
)
from sistemashn.comercial.ventas.models import Sale, SaleLine
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import ValidationError
from sistemashn.core.money import money
from sistemashn.core.pagination import Page

# Honduras no observa horario de verano: UTC-6 todo el año (igual que `comercial.credito.service`).
_HONDURAS_OFFSET = timedelta(hours=-6)

_REPORT_HEADERS: dict[str, tuple[str, ...]] = {
    "ventas_utilidad": ("numero", "fecha", "cliente_id", "total", "costo", "utilidad"),
    "stock_bajo": ("codigo", "nombre", "existencia", "reservado", "disponible", "minimo"),
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ReportService:
    """Reportes de ventas/utilidad, stock bajo, cuentas y cierres de caja, más export a Excel."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
        inventory: InventoryService | None = None,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.inventory = inventory

    # -- Ventas y utilidad ---------------------------------------------------

    def sales_and_profit(self, actor: Actor, since: datetime, until: datetime) -> SalesProfitReport:
        def _op(session: Session) -> SalesProfitReport:
            self.authorizer.require(session, actor, "com.reportes.ver")
            ver_costos = self.authorizer.can(session, actor, "com.costos.ver")

            ventas = session.scalars(
                select(Sale).where(
                    Sale.status == "confirmada",
                    Sale.sold_at >= since,
                    Sale.sold_at <= until,
                )
            ).all()

            rows: list[SalesProfitRow] = []
            for venta in sorted(ventas, key=lambda v: (v.sold_at, v.id)):
                lineas = session.scalars(select(SaleLine).where(SaleLine.sale_id == venta.id)).all()
                # El total de la venta viene de las líneas que sí llevan precio: las que NO son
                # componente de un kit (`kit_component_of IS NULL`); la línea de kit-encabezado ya
                # trae su `line_total` real. El costo suma `qty * unit_cost_snapshot` de TODAS las
                # líneas, pero para una venta con kit el costo del encabezado del kit está
                # duplicado en sus componentes (ver `SaleService._costo_kit`: el costo del
                # encabezado ya es el promedio de los componentes), así que solo se toma el costo
                # de las líneas SIN componentes propios (`kit_component_of IS NULL` cuando el
                # producto no es kit) o el de los COMPONENTES (`kit_component_of IS NOT NULL`)
                # cuando sí lo es: nunca ambos para la misma unidad vendida.
                lineas_kit_no = [li for li in lineas if li.kit_component_of is None]
                line_nos_con_componentes = {
                    li.kit_component_of for li in lineas if li.kit_component_of is not None
                }
                costo_total = Decimal("0")
                for linea in lineas_kit_no:
                    if linea.line_no in line_nos_con_componentes:
                        continue  # es un kit-encabezado: su costo real vive en sus componentes
                    costo_total += linea.qty * linea.unit_cost_snapshot
                for linea in lineas:
                    if linea.kit_component_of is not None:
                        costo_total += linea.qty * linea.unit_cost_snapshot

                total_venta = venta.total
                costo_venta = money(costo_total) if ver_costos else None
                utilidad = money(total_venta - costo_total) if ver_costos else None

                rows.append(
                    SalesProfitRow(
                        sale_id=venta.id,
                        number=venta.number,
                        sold_at=venta.sold_at,
                        customer_id=venta.customer_id,
                        total=total_venta,
                        cost=costo_venta,
                        profit=utilidad,
                    )
                )

            total_sales = money(sum((r.total for r in rows), Decimal("0")))
            if ver_costos:
                total_cost: Decimal | None = money(
                    sum((r.cost for r in rows if r.cost is not None), Decimal("0"))
                )
                total_profit: Decimal | None = money(total_sales - total_cost)
            else:
                total_cost = None
                total_profit = None

            return SalesProfitReport(
                rows=tuple(rows),
                total_sales=total_sales,
                total_cost=total_cost,
                total_profit=total_profit,
                since=since,
                until=until,
            )

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Stock bajo ---------------------------------------------------------

    def low_stock(self, actor: Actor, page: int = 1, page_size: int = 50) -> Page[LowStockRow]:
        if self.inventory is None:
            raise ValidationError(
                "el reporte de stock bajo no está disponible: no se inyectó InventoryService"
            )
        pagina = self.inventory.low_stock(actor, page=page, page_size=page_size)
        items = [
            LowStockRow(
                product_id=item.product_id,
                code=item.code,
                name=item.name,
                on_hand=item.on_hand,
                reserved=item.reserved,
                available=item.available,
                min_stock=item.min_stock,
            )
            for item in pagina.items
        ]
        return Page(items=items, total=pagina.total, page=pagina.page, page_size=pagina.page_size)

    # -- Saldos de cuentas ---------------------------------------------------

    def account_balances(self, actor: Actor, kind: str) -> list[AccountBalanceRow]:
        def _op(session: Session) -> list[AccountBalanceRow]:
            self.authorizer.require(session, actor, "com.reportes.ver")
            filas = session.execute(
                select(Account, Party)
                .join(Party, Account.party_id == Party.id)
                .where(Account.kind == kind)
            ).all()
            hoy = (self.clock() + _HONDURAS_OFFSET).date()
            resultado = []
            for cuenta, party in filas:
                if cuenta.balance == 0:
                    estado = "pagada"
                elif hoy > cuenta.due_date:
                    estado = "vencida"
                else:
                    estado = "pendiente"
                resultado.append(
                    AccountBalanceRow(
                        id=cuenta.id,
                        party_name=party.name,
                        kind=cuenta.kind,
                        balance=cuenta.balance,
                        due_date=cuenta.due_date,
                        status=estado,
                    )
                )
            resultado.sort(key=lambda r: (r.due_date, r.id))
            return resultado

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Cierres de caja ---------------------------------------------------

    def cash_closures(self, actor: Actor, since: datetime, until: datetime) -> list[CashClosureRow]:
        def _op(session: Session) -> list[CashClosureRow]:
            self.authorizer.require(session, actor, "com.reportes.ver")
            sesiones = session.scalars(
                select(CashSession).where(
                    CashSession.status == "cerrada",
                    CashSession.closed_at.is_not(None),
                    CashSession.closed_at >= since,
                    CashSession.closed_at <= until,
                )
            ).all()
            filas = [
                CashClosureRow(
                    id=s.id,
                    opened_at=s.opened_at,
                    closed_at=s.closed_at,  # type: ignore[arg-type]
                    opening_amount=s.opening_amount,
                    expected_cash=s.expected_cash,  # type: ignore[arg-type]
                    counted_cash=s.counted_cash,  # type: ignore[arg-type]
                    difference=s.difference,  # type: ignore[arg-type]
                )
                for s in sesiones
            ]
            filas.sort(key=lambda f: (f.closed_at, f.id))
            return filas

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Exportación a Excel ---------------------------------------------------

    def export_excel(
        self,
        actor: Actor,
        report_name: Literal["ventas_utilidad", "stock_bajo"],
        rows: list[Any],
        path: str | Path,
    ) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.reportes.ver")
            headers = _REPORT_HEADERS.get(report_name)
            if headers is None:
                raise ValidationError(f"reporte desconocido para exportar: '{report_name}'")

            wb = Workbook()
            ws = wb.active
            ws.title = report_name
            ws.append(list(headers))
            for cell in ws[1]:
                cell.font = Font(bold=True)

            if report_name == "ventas_utilidad":
                for row in rows:
                    ws.append(
                        [
                            row.number,
                            row.sold_at.isoformat(),
                            row.customer_id if row.customer_id is not None else "",
                            float(row.total),
                            float(row.cost) if row.cost is not None else "",
                            float(row.profit) if row.profit is not None else "",
                        ]
                    )
            elif report_name == "stock_bajo":
                for row in rows:
                    ws.append(
                        [
                            row.code,
                            row.name,
                            float(row.on_hand),
                            float(row.reserved),
                            float(row.available),
                            float(row.min_stock),
                        ]
                    )

            wb.save(path)

        run_in_transaction(self.factory, _op, readonly=True)
