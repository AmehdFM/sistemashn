"""Pruebas de construcción del POS con las mejoras de T7.5 (aparcar y resumen).

Sigue la convención del resto de `tests/comercial/ui/`: solo se prueba que la pantalla se
construye sin lanzar, ya que los controles de Flet 1.0 exigen estar adjuntos a una `Page` real
para `.update()`, lo cual no está disponible en estas pruebas (ver `test_pos_view.py`).
"""

import flet as ft

from sistemashn.comercial.ui.pos_view import build_pos_view


def _contiene_boton(control: ft.Control, texto: str) -> bool:
    if isinstance(control, (ft.FilledButton, ft.OutlinedButton)) and control.content == texto:
        return True
    for atributo in ("controls", "content", "actions"):
        valor = getattr(control, atributo, None)
        if valor is None:
            continue
        items = valor if isinstance(valor, list) else [valor]
        for item in items:
            if isinstance(item, ft.Control) and _contiene_boton(item, texto):
                return True
    return False


def test_build_pos_view_muestra_boton_aparcar_y_ventas_en_espera(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    root = build_pos_view(ctx)

    assert _contiene_boton(root, "Aparcar venta")
    assert _contiene_boton(root, "Ventas en espera (0)")


def test_build_pos_view_refleja_borradores_aparcados_del_usuario(
    ctx_factory, admin_actor, producto_id
):
    ctx = ctx_factory(admin_actor)
    store = ctx.service("parked_sales")
    store.park(admin_actor.user_id, {"lineas": [1], "pagos": [], "cliente": None})

    root = build_pos_view(ctx)

    assert _contiene_boton(root, "Ventas en espera (1)")


def test_build_pos_view_no_lanza_con_politica_de_impresion_never(
    ctx_factory, admin_actor, producto_id
):
    from sistemashn.core.settings.schemas import BusinessInput, OperationSettingsInput

    ctx = ctx_factory(admin_actor)
    settings = ctx.service("settings")
    settings.update_business(
        admin_actor,
        BusinessInput(
            name="Negocio", legal_name="Negocio SA", address="Dir", phone="1", email="a@b.com"
        ),
    )
    settings.update_operation_settings(
        admin_actor, OperationSettingsInput(print_receipt_policy="never")
    )

    control = build_pos_view(ctx)

    assert isinstance(control, ft.Control)
