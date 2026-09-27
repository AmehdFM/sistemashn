"""Pruebas de cotizaciones y apartados (plan T4.1)."""

from datetime import date
from decimal import Decimal

import pytest

from sistemashn.comercial.cotizaciones.errors import InvalidQuoteStatus
from sistemashn.comercial.cotizaciones.schemas import QuoteInput, QuoteLineInput
from sistemashn.comercial.inventario.errors import InsufficientStock
from sistemashn.comercial.inventario.models import Stock
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import PermissionDenied

VALID_UNTIL_FUTURO = date(2026, 10, 15)
VALID_UNTIL_PASADO = date(2026, 9, 25)


def _recibir(session_factory, inventory_ledger, admin_actor, product_id, qty, cost="10.00"):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, product_id, qty, Decimal(cost))

    run_in_transaction(session_factory, _op)


def _stock(session_factory, product_id) -> Stock:
    with session_factory() as session:
        return session.get(Stock, product_id)


def _quote_input(product_id, qty="1", reserve=True, request_id="req-1", **overrides) -> QuoteInput:
    data = {
        "lines": [QuoteLineInput(product_id=product_id, qty=Decimal(qty))],
        "valid_until": VALID_UNTIL_FUTURO,
        "reserve": reserve,
        "request_id": request_id,
    }
    data.update(overrides)
    return QuoteInput(**data)


# -- Creación y apartado simple -----------------------------------------------


def test_crear_cotizacion_sin_apartado(quote_service, admin_actor, producto_id):
    vista = quote_service.create(
        admin_actor, _quote_input(producto_id, reserve=False, request_id="r1")
    )
    assert vista.status == "abierta"
    assert vista.has_reservation is False
    assert vista.number == "Q-000001"
    assert vista.total > 0


def test_crear_cotizacion_con_apartado_reserva_stock(
    quote_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    _recibir(session_factory, inventory_ledger, admin_actor, producto_id, Decimal("10"))
    quote_service.create(admin_actor, _quote_input(producto_id, qty="3", request_id="r1"))
    stock = _stock(session_factory, producto_id)
    assert stock.reserved == Decimal("3.000")


def test_crear_cotizacion_kit_reserva_componentes_proporcionalmente(
    quote_service,
    session_factory,
    inventory_ledger,
    admin_actor,
    kit_id,
    componente_a_id,
    componente_b_id,
):
    _recibir(session_factory, inventory_ledger, admin_actor, componente_a_id, Decimal("10"))
    _recibir(session_factory, inventory_ledger, admin_actor, componente_b_id, Decimal("10"))

    quote_service.create(admin_actor, _quote_input(kit_id, qty="2", request_id="r1"))

    stock_a = _stock(session_factory, componente_a_id)
    stock_b = _stock(session_factory, componente_b_id)
    assert stock_a.reserved == Decimal("4.000")  # 2 kits x 2 unidades del componente A
    assert stock_b.reserved == Decimal("2.000")  # 2 kits x 1 unidad del componente B


def test_apartado_insuficiente_no_reserva_nada_de_las_demas_lineas(
    quote_service, session_factory, inventory_ledger, admin_actor, producto_id, producto_fraccion_id
):
    _recibir(session_factory, inventory_ledger, admin_actor, producto_id, Decimal("5"))
    _recibir(session_factory, inventory_ledger, admin_actor, producto_fraccion_id, Decimal("1"))

    data = QuoteInput(
        lines=[
            QuoteLineInput(product_id=producto_id, qty=Decimal("2")),
            QuoteLineInput(product_id=producto_fraccion_id, qty=Decimal("5")),
        ],
        valid_until=VALID_UNTIL_FUTURO,
        reserve=True,
        request_id="r1",
    )
    with pytest.raises(InsufficientStock):
        quote_service.create(admin_actor, data)

    assert _stock(session_factory, producto_id).reserved == Decimal("0.000")
    assert _stock(session_factory, producto_fraccion_id).reserved == Decimal("0.000")


def test_cantidad_fraccionaria(
    quote_service, session_factory, inventory_ledger, admin_actor, producto_fraccion_id
):
    _recibir(session_factory, inventory_ledger, admin_actor, producto_fraccion_id, Decimal("5"))
    quote_service.create(
        admin_actor, _quote_input(producto_fraccion_id, qty="1.5", request_id="r1")
    )
    stock = _stock(session_factory, producto_fraccion_id)
    assert stock.reserved == Decimal("1.500")


# -- Vencimiento perezoso -----------------------------------------------------


def test_vencimiento_libera_reservas_al_consultar(
    quote_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    _recibir(session_factory, inventory_ledger, admin_actor, producto_id, Decimal("10"))
    vista = quote_service.create(
        admin_actor,
        _quote_input(producto_id, qty="3", request_id="r1", valid_until=VALID_UNTIL_PASADO),
    )

    consultada = quote_service.get(admin_actor, vista.id)
    assert consultada.status == "vencida"
    assert _stock(session_factory, producto_id).reserved == Decimal("0.000")


def test_consultar_dos_veces_una_vencida_no_duplica_liberacion(
    quote_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    _recibir(session_factory, inventory_ledger, admin_actor, producto_id, Decimal("10"))
    vista = quote_service.create(
        admin_actor,
        _quote_input(producto_id, qty="3", request_id="r1", valid_until=VALID_UNTIL_PASADO),
    )

    quote_service.get(admin_actor, vista.id)
    quote_service.get(admin_actor, vista.id)

    stock = _stock(session_factory, producto_id)
    assert stock.reserved == Decimal("0.000")
    assert stock.on_hand == Decimal("10.000")


# -- Cancelación --------------------------------------------------------------


def test_cancelar_libera_reservas(
    quote_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    _recibir(session_factory, inventory_ledger, admin_actor, producto_id, Decimal("10"))
    vista = quote_service.create(admin_actor, _quote_input(producto_id, qty="3", request_id="r1"))

    quote_service.cancel(admin_actor, vista.id)

    consultada = quote_service.get(admin_actor, vista.id)
    assert consultada.status == "cancelada"
    assert _stock(session_factory, producto_id).reserved == Decimal("0.000")


def test_cancelar_dos_veces_falla_la_segunda(quote_service, admin_actor, producto_id):
    vista = quote_service.create(
        admin_actor, _quote_input(producto_id, reserve=False, request_id="r1")
    )
    quote_service.cancel(admin_actor, vista.id)
    with pytest.raises(InvalidQuoteStatus):
        quote_service.cancel(admin_actor, vista.id)


# -- Competencia por el mismo stock -------------------------------------------


def test_dos_cotizaciones_compitiendo_por_el_mismo_stock(
    quote_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    _recibir(session_factory, inventory_ledger, admin_actor, producto_id, Decimal("5"))
    quote_service.create(admin_actor, _quote_input(producto_id, qty="4", request_id="r1"))

    with pytest.raises(InsufficientStock):
        quote_service.create(admin_actor, _quote_input(producto_id, qty="2", request_id="r2"))


# -- Permisos ------------------------------------------------------------------


def test_crear_sin_permiso_gestionar_falla(
    quote_service, vendedor_actor, bodega_actor, producto_id
):
    with pytest.raises(PermissionDenied):
        quote_service.create(
            bodega_actor, _quote_input(producto_id, reserve=False, request_id="r1")
        )


def test_cancelar_sin_permiso_gestionar_falla(
    quote_service, admin_actor, bodega_actor, producto_id
):
    vista = quote_service.create(
        admin_actor, _quote_input(producto_id, reserve=False, request_id="r1")
    )
    with pytest.raises(PermissionDenied):
        quote_service.cancel(bodega_actor, vista.id)


def test_consultar_sin_permiso_ver_falla(quote_service, admin_actor, bodega_actor, producto_id):
    vista = quote_service.create(
        admin_actor, _quote_input(producto_id, reserve=False, request_id="r1")
    )
    with pytest.raises(PermissionDenied):
        quote_service.get(bodega_actor, vista.id)
