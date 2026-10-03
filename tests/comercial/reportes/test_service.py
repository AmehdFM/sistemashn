"""Pruebas de `ReportService` (plan T5.5)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from sistemashn.comercial.devoluciones.models import CustomerReturn
from sistemashn.comercial.ventas.models import SaleLine
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.models import UserPermission
from sistemashn.core.errors import PermissionDenied, ValidationError
from sistemashn.core.identity.models import User

from .conftest import anular_venta_directo, confirmar_compra, confirmar_venta

DESDE = datetime(2020, 1, 1, tzinfo=UTC)
HASTA = datetime(2030, 1, 1, tzinfo=UTC)


def _actor_sin_costos(session_factory, now) -> Actor:
    """Perfil vendedor: tiene `com.reportes.ver` (por herencia) pero no `com.costos.ver`."""
    with session_factory() as session:
        user = User(
            username="vendedor_reportes",
            full_name="Usuario vendedor_reportes",
            password_hash="hash",
            is_admin=False,
            is_active=True,
            profile_code="vendedor",
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.flush()
        session.add(
            UserPermission(user_id=user.id, permission_code="com.reportes.ver", granted=True)
        )
        session.commit()
        user_id = user.id
    return Actor(user_id=user_id, username="vendedor_reportes", is_admin=False, session_id="s-vr")


class TestSalesAndProfit:
    def test_excluye_isv_y_descuenta_devolucion_vendible_con_costo_historico(
        self,
        report_service,
        purchase_service,
        sale_service,
        session_factory,
        admin_actor,
        proveedor_id,
        producto_id,
        now,
    ):
        from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
        from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput

        confirmar_compra(purchase_service, admin_actor, proveedor_id, producto_id, "10", "70")
        venta = sale_service.confirm(
            admin_actor,
            SaleInput(
                customer_id=None,
                lines=[
                    SaleLineInput(
                        product_id=producto_id,
                        qty=Decimal("2"),
                        unit_price=Decimal("150"),
                        tax_rate=Decimal("0.15"),
                    )
                ],
                payments=[PaymentInput(method=PaymentMethod.TARJETA, amount=Decimal("345"))],
                request_id="reporte-gravado-devolucion",
            ),
        )
        with session_factory() as session:
            linea = session.query(SaleLine).filter_by(sale_id=venta.id).one()
            session.add(
                CustomerReturn(
                    sale_line_id=linea.id,
                    product_id=None,
                    unit_price_override=None,
                    qty=Decimal("1"),
                    condition="vendible",
                    resolution="reembolso",
                    amount=Decimal("150"),
                    new_sale_id=None,
                    user_id=admin_actor.user_id,
                    reason=None,
                    created_at=now,
                )
            )
            session.commit()
        confirmar_compra(purchase_service, admin_actor, proveedor_id, producto_id, "10", "90")

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)

        assert reporte.total_sales == Decimal("150.00")
        assert reporte.total_cost == Decimal("70.00")
        assert reporte.total_profit == Decimal("80.00")

    def test_devolucion_no_vendible_reduce_ingreso_pero_no_recupera_costo(
        self,
        report_service,
        purchase_service,
        sale_service,
        session_factory,
        admin_actor,
        proveedor_id,
        producto_id,
        now,
    ):
        confirmar_compra(purchase_service, admin_actor, proveedor_id, producto_id, "2", "70")
        venta = confirmar_venta(sale_service, admin_actor, producto_id, "2", "150")
        with session_factory() as session:
            linea = session.query(SaleLine).filter_by(sale_id=venta.id).one()
            session.add(
                CustomerReturn(
                    sale_line_id=linea.id,
                    product_id=None,
                    unit_price_override=None,
                    qty=Decimal("1"),
                    condition="no_vendible",
                    resolution="reembolso",
                    amount=Decimal("150"),
                    new_sale_id=None,
                    user_id=admin_actor.user_id,
                    reason=None,
                    created_at=now,
                )
            )
            session.commit()

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)
        assert reporte.total_sales == Decimal("150.00")
        assert reporte.total_cost == Decimal("140.00")
        assert reporte.total_profit == Decimal("10.00")

    def test_backorder_deja_margen_sin_calcular(
        self,
        report_service,
        purchase_service,
        sale_service,
        session_factory,
        admin_actor,
        proveedor_id,
        producto_id,
    ):
        confirmar_compra(purchase_service, admin_actor, proveedor_id, producto_id, "1", "70")
        venta = confirmar_venta(sale_service, admin_actor, producto_id, "1", "150")
        with session_factory() as session:
            linea = session.query(SaleLine).filter_by(sale_id=venta.id).one()
            linea.backorder_qty = Decimal("1")
            session.commit()

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)
        assert reporte.incomplete_cost_sales == 1
        assert reporte.rows[0].cost is None
        assert reporte.rows[0].profit is None
        assert reporte.total_cost is None
        assert reporte.total_profit is None

    def test_devolucion_sin_comprobante_queda_identificada_sin_inventar_margen(
        self,
        report_service,
        session_factory,
        admin_actor,
        producto_id,
        now,
    ):
        with session_factory() as session:
            session.add(
                CustomerReturn(
                    sale_line_id=None,
                    product_id=producto_id,
                    unit_price_override=Decimal("20"),
                    qty=Decimal("1"),
                    condition="vendible",
                    resolution="reembolso",
                    amount=Decimal("20"),
                    new_sale_id=None,
                    user_id=admin_actor.user_id,
                    reason=None,
                    created_at=now,
                )
            )
            session.commit()

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)
        assert reporte.unlinked_returns == 1
        assert reporte.rows == ()

    def test_utilidad_usa_costo_historico_no_promedio_recalculado(
        self,
        report_service,
        purchase_service,
        sale_service,
        admin_actor,
        proveedor_id,
        producto_id,
    ):
        # Compra inicial a 50.00: el stock queda con avg_cost=50.00.
        confirmar_compra(purchase_service, admin_actor, proveedor_id, producto_id, "10", "50.00")
        # Venta de 2 unidades a 150.00: el costo histórico snapshot debe ser 50.00.
        confirmar_venta(sale_service, admin_actor, producto_id, "2", "150.00")
        # Compra posterior a un costo distinto: NO debe alterar el costo ya reportado de la venta.
        confirmar_compra(purchase_service, admin_actor, proveedor_id, producto_id, "10", "80.00")

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)

        assert len(reporte.rows) == 1
        fila = reporte.rows[0]
        assert fila.total == Decimal("300.00")
        assert fila.cost == Decimal("100.00")  # 2 * 50.00, no 2 * 80.00
        assert fila.profit == Decimal("200.00")
        assert reporte.total_sales == Decimal("300.00")
        assert reporte.total_cost == Decimal("100.00")
        assert reporte.total_profit == Decimal("200.00")

    def test_utilidad_de_venta_con_kit_suma_costo_de_componentes_no_del_encabezado(
        self,
        report_service,
        inventory_ledger,
        session_factory,
        sale_service,
        admin_actor,
        kit_id,
        componente_a_id,
        componente_b_id,
    ):
        # Kit: 2 unidades de A + 1 de B. Se les da entrada a costos distintos.
        from sistemashn.core.db.uow import run_in_transaction

        from .conftest import confirmar_venta as _cv

        def _recibir(session):
            inventory_ledger.receive(
                session, admin_actor, componente_a_id, Decimal("10"), Decimal("20.00")
            )
            inventory_ledger.receive(
                session, admin_actor, componente_b_id, Decimal("10"), Decimal("30.00")
            )

        run_in_transaction(session_factory, _recibir)

        # Vende 1 kit a 200.00.
        _cv(sale_service, admin_actor, kit_id, "1", "200.00")

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)

        assert len(reporte.rows) == 1
        fila = reporte.rows[0]
        # Costo esperado: 2 componentes A a 20.00 + 1 componente B a 30.00 = 70.00.
        # El costo del encabezado del kit (promedio 70.00/1 = 70.0000) NO se suma de nuevo.
        assert fila.cost == Decimal("70.00")
        assert fila.total == Decimal("200.00")
        assert fila.profit == Decimal("130.00")

    def test_excluye_ventas_anuladas(
        self,
        report_service,
        session_factory,
        sale_service,
        admin_actor,
        producto_id,
        inventory_ledger,
    ):
        from sistemashn.core.db.uow import run_in_transaction

        def _recibir(session):
            inventory_ledger.receive(
                session, admin_actor, producto_id, Decimal("10"), Decimal("50.00")
            )

        run_in_transaction(session_factory, _recibir)

        venta = confirmar_venta(sale_service, admin_actor, producto_id, "1", "150.00")
        anular_venta_directo(session_factory, venta.id)

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)

        assert reporte.rows == ()
        assert reporte.total_sales == Decimal("0.00")

    def test_rango_vacio_sin_ventas_devuelve_ceros(self, report_service, admin_actor):
        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)
        assert reporte.rows == ()
        assert reporte.total_sales == Decimal("0.00")
        assert reporte.total_cost == Decimal("0.00")
        assert reporte.total_profit == Decimal("0.00")

    def test_oculta_costos_sin_permiso_com_costos_ver(
        self,
        report_service,
        session_factory,
        now,
        sale_service,
        admin_actor,
        producto_id,
        inventory_ledger,
    ):
        from sistemashn.core.db.uow import run_in_transaction

        def _recibir(session):
            inventory_ledger.receive(
                session, admin_actor, producto_id, Decimal("10"), Decimal("50.00")
            )

        run_in_transaction(session_factory, _recibir)
        confirmar_venta(sale_service, admin_actor, producto_id, "1", "150.00")

        actor_limitado = _actor_sin_costos(session_factory, now)
        reporte = report_service.sales_and_profit(actor_limitado, DESDE, HASTA)

        assert reporte.rows[0].cost is None
        assert reporte.rows[0].profit is None
        assert reporte.total_cost is None
        assert reporte.total_profit is None
        assert reporte.total_sales == Decimal("150.00")


class TestLowStock:
    def test_sin_inventory_inyectado_falla_con_mensaje_claro(
        self, report_service_sin_inventario, admin_actor
    ):
        with pytest.raises(ValidationError, match="InventoryService"):
            report_service_sin_inventario.low_stock(admin_actor)

    def test_con_inventory_inyectado_funciona(self, report_service, admin_actor, producto_id):
        # `producto_id` nace con on_hand=0 y min_stock=2 (fixture `make_product_input`), por lo
        # que ya aparece en el reporte de stock bajo sin necesidad de ajustar nada.
        pagina = report_service.low_stock(admin_actor)
        assert pagina.total == 1
        assert pagina.items[0].product_id == producto_id

    def test_low_stock_lista_productos_bajo_minimo(self, report_service, admin_actor, producto_id):
        pagina = report_service.low_stock(admin_actor)
        assert pagina.total == 1
        assert pagina.items[0].product_id == producto_id


class TestAccountBalances:
    def test_refleja_saldos_para_payable_y_receivable(
        self,
        report_service,
        purchase_service,
        sale_service,
        admin_actor,
        proveedor_id,
        cliente_id,
        producto_id,
        inventory_ledger,
        session_factory,
        fecha_vencimiento,
    ):
        from decimal import Decimal as D

        from sistemashn.comercial.compras.schemas import PurchaseInput, PurchaseLineInput
        from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput
        from sistemashn.core.db.uow import run_in_transaction

        def _recibir(session):
            inventory_ledger.receive(session, admin_actor, producto_id, D("10"), D("50.00"))

        run_in_transaction(session_factory, _recibir)

        purchase_service.confirm(
            admin_actor,
            PurchaseInput(
                supplier_id=proveedor_id,
                lines=[
                    PurchaseLineInput(
                        product_id=producto_id, qty=D("5"), unit_cost=D("50.00"), tax_rate=D("0")
                    )
                ],
                payments=[],
                credit_due_date=fecha_vencimiento,
                request_id="compra-credito-1",
            ),
        )
        sale_service.confirm(
            admin_actor,
            SaleInput(
                customer_id=cliente_id,
                lines=[
                    SaleLineInput(
                        product_id=producto_id, qty=D("1"), unit_price=D("150.00"), tax_rate=D("0")
                    )
                ],
                payments=[],
                credit_due_date=fecha_vencimiento,
                request_id="venta-credito-1",
            ),
        )

        payables = report_service.account_balances(admin_actor, "payable")
        receivables = report_service.account_balances(admin_actor, "receivable")

        assert len(payables) == 1
        assert payables[0].balance == D("250.00")
        assert payables[0].kind == "payable"
        assert payables[0].status == "pendiente"

        assert len(receivables) == 1
        assert receivables[0].balance == D("150.00")
        assert receivables[0].kind == "receivable"


class TestCashClosures:
    def test_solo_incluye_sesiones_cerradas_en_el_rango(
        self, report_service, cash_service, admin_actor
    ):
        cash_service.open(admin_actor, Decimal("100.00"))
        cerrada = cash_service.close(admin_actor, Decimal("100.00"))

        cierres = report_service.cash_closures(admin_actor, DESDE, HASTA)

        assert len(cierres) == 1
        assert cierres[0].id == cerrada.id
        assert cierres[0].expected_cash == Decimal("100.00")
        assert cierres[0].difference == Decimal("0.00")

    def test_rango_sin_cierres_devuelve_vacio(self, report_service, admin_actor):
        cierres = report_service.cash_closures(
            admin_actor, datetime(2000, 1, 1, tzinfo=UTC), datetime(2000, 1, 2, tzinfo=UTC)
        )
        assert cierres == []


class TestExportExcel:
    def test_ventas_utilidad_produce_xlsx_valido(
        self,
        report_service,
        tmp_path,
        sale_service,
        admin_actor,
        producto_id,
        inventory_ledger,
        session_factory,
    ):
        from sistemashn.core.db.uow import run_in_transaction

        def _recibir(session):
            inventory_ledger.receive(
                session, admin_actor, producto_id, Decimal("10"), Decimal("50.00")
            )

        run_in_transaction(session_factory, _recibir)
        confirmar_venta(sale_service, admin_actor, producto_id, "1", "150.00")

        reporte = report_service.sales_and_profit(admin_actor, DESDE, HASTA)
        path = tmp_path / "ventas.xlsx"

        report_service.export_excel(admin_actor, "ventas_utilidad", list(reporte.rows), path)

        wb = load_workbook(path)
        ws = wb.active
        encabezados = [c.value for c in ws[1]]
        assert encabezados == ["numero", "fecha", "cliente_id", "total", "costo", "utilidad"]
        fila = [c.value for c in ws[2]]
        assert fila[0] == reporte.rows[0].number
        assert fila[3] == 150.0

    def test_reporte_desconocido_falla(self, report_service, admin_actor, tmp_path):
        with pytest.raises(ValidationError, match="desconocido"):
            report_service.export_excel(admin_actor, "otro", [], tmp_path / "x.xlsx")


class TestPermisos:
    def test_sin_permiso_falla(self, report_service, session_factory, now):
        with session_factory() as session:
            user = User(
                username="sin_permiso",
                full_name="Usuario sin_permiso",
                password_hash="hash",
                is_admin=False,
                is_active=True,
                profile_code=None,
                permissions_version=1,
                failed_attempts=0,
                locked_until=None,
                must_change_password=False,
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            session.commit()
            user_id = user.id
        actor = Actor(user_id=user_id, username="sin_permiso", is_admin=False, session_id="s-sp")

        with pytest.raises(PermissionDenied):
            report_service.sales_and_profit(actor, DESDE, HASTA)
