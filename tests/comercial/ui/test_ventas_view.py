"""Pruebas de la pantalla de historial de ventas."""

import flet as ft

from sistemashn.comercial.ui.ventas_view import build_sales_view


def test_build_sales_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_sales_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_sales_view_con_venta_no_lanza(ctx_factory, admin_actor, producto_id):
    from decimal import Decimal

    from sistemashn.comercial.inventario.service import InventoryService
    from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
    from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput
    from sistemashn.comercial.ventas.service import SaleService

    ctx = ctx_factory(admin_actor)
    inventory: InventoryService = ctx.service("inventory")
    inventory.adjust(
        admin_actor,
        producto_id,
        Decimal("10"),
        "carga inicial",
        unit_cost=Decimal("50.00"),
    )
    sales: SaleService = ctx.service("sales")
    sales.confirm(
        admin_actor,
        SaleInput(
            lines=[SaleLineInput(product_id=producto_id, qty="1")],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount="172.50")],
            request_id="req-venta-1",
        ),
    )

    control = build_sales_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_sales_view_vendedor_sin_permiso_no_lanza(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_sales_view(ctx)

    assert isinstance(control, ft.Control)
