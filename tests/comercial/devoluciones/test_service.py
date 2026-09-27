"""Pruebas de `ReturnService`: devoluciones de cliente y a proveedor (plan T5.2/T5.3)."""

from decimal import Decimal

import pytest

from sistemashn.comercial.credito.schemas import AccountKind
from sistemashn.comercial.devoluciones.errors import ReturnExceedsOriginal
from sistemashn.comercial.devoluciones.schemas import (
    CustomerReturnInput,
    CustomerReturnResolution,
    ReturnCondition,
    SupplierReturnInput,
    SupplierReturnResolution,
)
from sistemashn.comercial.inventario.models import Stock
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import PermissionDenied, ValidationError


def _customer_input(sale_line_id, qty, *, condition, resolution, payment=None, request_id="dev-1"):
    return CustomerReturnInput(
        sale_line_id=sale_line_id,
        qty=Decimal(qty),
        condition=condition,
        resolution=resolution,
        payment=payment,
        request_id=request_id,
    )


def _supplier_input(purchase_line_id, qty, *, resolution, request_id="dev-p-1"):
    return SupplierReturnInput(
        purchase_line_id=purchase_line_id,
        qty=Decimal(qty),
        resolution=resolution,
        request_id=request_id,
    )


def _stock(session_factory, product_id) -> Stock:
    def _op(session):
        stock = session.get(Stock, product_id)
        session.expunge(stock)
        return stock

    return run_in_transaction(session_factory, _op, readonly=True)


# -- Devoluciones de cliente ---------------------------------------------------------


def test_devoluciones_parciales_acumuladas_no_exceden_lo_vendido(
    return_service, admin_actor, sale_line_id
):
    # `venta_confirmada` (vía `sale_line_id`) vendió 5 unidades.
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "2",
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
            request_id="dev-parcial-1",
        ),
    )
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "2",
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
            request_id="dev-parcial-2",
        ),
    )

    with pytest.raises(ReturnExceedsOriginal):
        return_service.customer_return(
            admin_actor,
            _customer_input(
                sale_line_id,
                "2",
                condition=ReturnCondition.VENDIBLE,
                resolution=CustomerReturnResolution.CAMBIO,
                request_id="dev-parcial-3",
            ),
        )


def test_devolucion_vendible_aumenta_on_hand(
    return_service, session_factory, admin_actor, venta_confirmada, sale_line_id
):
    antes = _stock(session_factory, venta_confirmada.lines[0].product_id)
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "2",
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
        ),
    )
    despues = _stock(session_factory, venta_confirmada.lines[0].product_id)
    assert despues.on_hand == antes.on_hand + Decimal("2")
    assert despues.unsellable == antes.unsellable


def test_devolucion_no_vendible_aumenta_unsellable_no_on_hand(
    return_service, session_factory, admin_actor, venta_confirmada, sale_line_id
):
    antes = _stock(session_factory, venta_confirmada.lines[0].product_id)
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "1",
            condition=ReturnCondition.NO_VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
        ),
    )
    despues = _stock(session_factory, venta_confirmada.lines[0].product_id)
    assert despues.on_hand == antes.on_hand
    assert despues.unsellable == antes.unsellable + Decimal("1")


def test_cambio_sin_venta_nueva_no_falla_y_se_enlaza_despues(
    return_service, admin_actor, venta_confirmada, sale_line_id
):
    vista = return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "1",
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
        ),
    )
    assert vista.new_sale_id is None

    enlazada = return_service.link_exchange_sale(admin_actor, vista.id, venta_confirmada.id)
    assert enlazada.new_sale_id == venta_confirmada.id


def test_saldo_a_favor_crea_cuenta_consultable_y_pagable(
    return_service, account_service, admin_actor, sale_line_id
):
    vista = return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "2",
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.SALDO_A_FAVOR,
        ),
    )
    cuenta = account_service.list(admin_actor, AccountKind.CREDIT_NOTE).items[0]
    assert cuenta.original_amount == vista.amount
    assert cuenta.balance == vista.amount

    pagada = account_service.pay(
        admin_actor,
        cuenta.id,
        PaymentInput(method=PaymentMethod.EFECTIVO, amount=vista.amount),
        request_id="pago-saldo-favor-1",
    )
    assert pagada.balance == Decimal("0.00")


def test_reembolso_sin_pago_falla_validacion(sale_line_id):
    with pytest.raises(ValueError):
        _customer_input(
            sale_line_id,
            "1",
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.REEMBOLSO,
        )


def test_reembolso_con_pago_no_falla(return_service, admin_actor, sale_line_id):
    vista = return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "1",
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.REEMBOLSO,
            payment=PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50")),
        ),
    )
    assert vista.resolution == "reembolso"


def test_reintento_con_mismo_request_id_no_duplica(return_service, admin_actor, sale_line_id):
    entrada = _customer_input(
        sale_line_id,
        "1",
        condition=ReturnCondition.VENDIBLE,
        resolution=CustomerReturnResolution.CAMBIO,
        request_id="dev-repetido",
    )
    primera = return_service.customer_return(admin_actor, entrada)
    segunda = return_service.customer_return(admin_actor, entrada)
    assert primera.id == segunda.id


def test_sin_permiso_falla(return_service, sin_permiso_actor, sale_line_id):
    with pytest.raises(PermissionDenied):
        return_service.customer_return(
            sin_permiso_actor,
            _customer_input(
                sale_line_id,
                "1",
                condition=ReturnCondition.VENDIBLE,
                resolution=CustomerReturnResolution.CAMBIO,
            ),
        )


# -- Devoluciones a proveedor ---------------------------------------------------------


def test_devolucion_proveedor_parcial_no_excede_lo_comprado(
    return_service, session_factory, admin_actor, sale_line_id, purchase_line_id
):
    # `sale_line_id` fuerza a `venta_confirmada` a existir, dejando 5 de 10 en `unsellable` sería
    # incorrecto: aquí se mueve directo a `unsellable` con una devolución de cliente no vendible
    # para tener stock defectuoso disponible antes de devolverlo al proveedor.
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "3",
            condition=ReturnCondition.NO_VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
            request_id="dev-para-proveedor",
        ),
    )

    return_service.supplier_return(
        admin_actor,
        _supplier_input(
            purchase_line_id,
            "2",
            resolution=SupplierReturnResolution.REEMBOLSO,
            request_id="dev-prov-1",
        ),
    )
    return_service.supplier_return(
        admin_actor,
        _supplier_input(
            purchase_line_id,
            "1",
            resolution=SupplierReturnResolution.REEMBOLSO,
            request_id="dev-prov-2",
        ),
    )

    with pytest.raises(ReturnExceedsOriginal):
        return_service.supplier_return(
            admin_actor,
            _supplier_input(
                purchase_line_id,
                "8",
                resolution=SupplierReturnResolution.REEMBOLSO,
                request_id="dev-prov-3",
            ),
        )


def test_devolucion_proveedor_reemplazo_reingresa_a_on_hand(
    return_service,
    session_factory,
    admin_actor,
    sale_line_id,
    purchase_line_id,
    producto_devolucion_id,
):
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "2",
            condition=ReturnCondition.NO_VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
            request_id="dev-para-proveedor-reemplazo",
        ),
    )
    antes = _stock(session_factory, producto_devolucion_id)

    return_service.supplier_return(
        admin_actor,
        _supplier_input(purchase_line_id, "2", resolution=SupplierReturnResolution.REEMPLAZO),
    )

    despues = _stock(session_factory, producto_devolucion_id)
    assert despues.on_hand == antes.on_hand + Decimal("2")
    assert despues.unsellable == antes.unsellable - Decimal("2")


def test_credito_futuro_reduce_saldo_de_cxp_una_sola_vez_por_devolucion(
    return_service,
    account_service,
    admin_actor,
    sale_line_id,
    purchase_line_id_credito,
    compra_a_credito,
):
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "4",
            condition=ReturnCondition.NO_VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
            request_id="dev-para-credito-futuro",
        ),
    )

    cuenta_antes = account_service.list(admin_actor, AccountKind.PAYABLE).items[0]
    saldo_inicial = cuenta_antes.balance

    return_service.supplier_return(
        admin_actor,
        _supplier_input(
            purchase_line_id_credito,
            "2",
            resolution=SupplierReturnResolution.CREDITO_FUTURO,
            request_id="dev-credito-1",
        ),
    )
    cuenta_1 = account_service.get(admin_actor, cuenta_antes.id)
    assert cuenta_1.balance == saldo_inicial - Decimal("100.00")

    return_service.supplier_return(
        admin_actor,
        _supplier_input(
            purchase_line_id_credito,
            "1",
            resolution=SupplierReturnResolution.CREDITO_FUTURO,
            request_id="dev-credito-2",
        ),
    )
    cuenta_2 = account_service.get(admin_actor, cuenta_antes.id)
    assert cuenta_2.balance == saldo_inicial - Decimal("100.00") - Decimal("50.00")

    # Reintentar la primera devolución (mismo request_id) no repite el ajuste.
    return_service.supplier_return(
        admin_actor,
        _supplier_input(
            purchase_line_id_credito,
            "2",
            resolution=SupplierReturnResolution.CREDITO_FUTURO,
            request_id="dev-credito-1",
        ),
    )
    cuenta_3 = account_service.get(admin_actor, cuenta_antes.id)
    assert cuenta_3.balance == cuenta_2.balance


def test_sin_permiso_falla_en_devolucion_proveedor(
    return_service, sin_permiso_actor, purchase_line_id
):
    with pytest.raises(PermissionDenied):
        return_service.supplier_return(
            sin_permiso_actor,
            _supplier_input(purchase_line_id, "1", resolution=SupplierReturnResolution.REEMBOLSO),
        )


def test_reintento_supplier_con_mismo_request_id_no_duplica(
    return_service, admin_actor, sale_line_id, purchase_line_id
):
    return_service.customer_return(
        admin_actor,
        _customer_input(
            sale_line_id,
            "1",
            condition=ReturnCondition.NO_VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
            request_id="dev-para-reintento-proveedor",
        ),
    )
    entrada = _supplier_input(
        purchase_line_id,
        "1",
        resolution=SupplierReturnResolution.REEMBOLSO,
        request_id="dev-prov-repetido",
    )
    primera = return_service.supplier_return(admin_actor, entrada)
    segunda = return_service.supplier_return(admin_actor, entrada)
    assert primera.id == segunda.id


# -- T7.3: devolución "sin comprobante" ---------------------------------


def test_customer_return_sin_comprobante_requiere_product_id_y_precio(sale_line_id):
    with pytest.raises(ValueError):
        CustomerReturnInput(
            sale_line_id=None,
            qty=Decimal("1"),
            condition=ReturnCondition.VENDIBLE,
            resolution=CustomerReturnResolution.CAMBIO,
            request_id="dev-sc-invalido",
        )


def test_customer_return_sin_comprobante_crea_registro_con_monto_indicado(
    return_service, session_factory, admin_actor, producto_devolucion_id
):
    entrada = CustomerReturnInput(
        sale_line_id=None,
        product_id=producto_devolucion_id,
        unit_price_override=Decimal("80.00"),
        qty=Decimal("2"),
        condition=ReturnCondition.VENDIBLE,
        resolution=CustomerReturnResolution.CAMBIO,
        request_id="dev-sin-comprobante-1",
    )
    vista = return_service.customer_return(admin_actor, entrada)

    assert vista.sale_line_id is None
    assert vista.product_id == producto_devolucion_id
    assert vista.amount == Decimal("160.00")

    stock = _stock(session_factory, producto_devolucion_id)
    assert stock.on_hand == Decimal("2.000")


def test_customer_return_sin_comprobante_no_acumula_contra_ninguna_linea(
    return_service, admin_actor, producto_devolucion_id
):
    entrada_1 = CustomerReturnInput(
        sale_line_id=None,
        product_id=producto_devolucion_id,
        unit_price_override=Decimal("80.00"),
        qty=Decimal("50"),
        condition=ReturnCondition.VENDIBLE,
        resolution=CustomerReturnResolution.CAMBIO,
        request_id="dev-sin-comprobante-a",
    )
    entrada_2 = CustomerReturnInput(
        sale_line_id=None,
        product_id=producto_devolucion_id,
        unit_price_override=Decimal("80.00"),
        qty=Decimal("50"),
        condition=ReturnCondition.VENDIBLE,
        resolution=CustomerReturnResolution.CAMBIO,
        request_id="dev-sin-comprobante-b",
    )
    # Sin línea de referencia no hay tope que exceder: ambas se registran sin error.
    return_service.customer_return(admin_actor, entrada_1)
    return_service.customer_return(admin_actor, entrada_2)


def test_customer_return_sin_comprobante_saldo_a_favor_falla(
    return_service, admin_actor, producto_devolucion_id
):
    entrada = CustomerReturnInput(
        sale_line_id=None,
        product_id=producto_devolucion_id,
        unit_price_override=Decimal("80.00"),
        qty=Decimal("1"),
        condition=ReturnCondition.VENDIBLE,
        resolution=CustomerReturnResolution.SALDO_A_FAVOR,
        request_id="dev-sin-comprobante-saldo",
    )
    with pytest.raises(ValidationError):
        return_service.customer_return(admin_actor, entrada)


def test_supplier_return_sin_comprobante_requiere_product_id_y_precio(purchase_line_id):
    with pytest.raises(ValueError):
        SupplierReturnInput(
            purchase_line_id=None,
            qty=Decimal("1"),
            resolution=SupplierReturnResolution.REEMBOLSO,
            request_id="dev-prov-sc-invalido",
        )


def test_supplier_return_sin_comprobante_crea_registro_con_monto_indicado(
    return_service, session_factory, admin_actor, producto_devolucion_id, compra_confirmada
):
    # La pieza defectuosa debe estar en `unsellable` antes de devolverla al proveedor.
    from sistemashn.comercial.inventario.ledger import InventoryLedger

    with session_factory() as session:
        InventoryLedger(clock=lambda: return_service.clock()).move_to_unsellable(
            session,
            admin_actor,
            producto_devolucion_id,
            Decimal("2"),
            Decimal("50.00"),
            ref_type="ajuste_prueba",
            ref_id="1",
        )
        session.commit()

    entrada = SupplierReturnInput(
        purchase_line_id=None,
        product_id=producto_devolucion_id,
        unit_price_override=Decimal("45.00"),
        qty=Decimal("2"),
        resolution=SupplierReturnResolution.REEMBOLSO,
        request_id="dev-prov-sin-comprobante-1",
    )
    vista = return_service.supplier_return(admin_actor, entrada)

    assert vista.purchase_line_id is None
    assert vista.product_id == producto_devolucion_id
    assert vista.amount == Decimal("90.00")


def test_supplier_return_sin_comprobante_credito_futuro_falla(
    return_service, admin_actor, producto_devolucion_id
):
    entrada = SupplierReturnInput(
        purchase_line_id=None,
        product_id=producto_devolucion_id,
        unit_price_override=Decimal("45.00"),
        qty=Decimal("1"),
        resolution=SupplierReturnResolution.CREDITO_FUTURO,
        request_id="dev-prov-sin-comprobante-credito",
    )
    with pytest.raises(ValidationError):
        return_service.supplier_return(admin_actor, entrada)
