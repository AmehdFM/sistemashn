"""Pruebas de la pantalla de ajustes de operación: valores actuales, guardado y validación."""

from decimal import Decimal
from unittest.mock import MagicMock

import flet as ft

from sistemashn.core.settings.schemas import BusinessInput, OperationSettingsInput
from sistemashn.core.ui.views.operation_settings_view import build_operation_settings_view


def _crear_negocio(ctx, actor) -> None:
    ctx.service("settings").update_business(
        actor,
        BusinessInput(
            name="Repuestos ACME",
            legal_name="Repuestos ACME S. de R.L.",
            rtn=None,
            address="Col. Kennedy",
            phone="9999-9999",
            email="ventas@acme.hn",
        ),
    )


def test_build_operation_settings_view_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_operation_settings_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_operation_settings_view_refleja_valores_actuales(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)
    _crear_negocio(ctx, admin_actor)
    ctx.service("settings").update_operation_settings(
        admin_actor,
        OperationSettingsInput(
            cash_session_required=False,
            block_sale_without_stock=False,
            max_discount_percent=Decimal("0.35"),
            default_credit_days=45,
        ),
    )

    control = build_operation_settings_view(ctx)

    assert isinstance(control, ft.Control)
    campos = _todos_los_controles(control)
    campo_descuento = next(c for c in campos if getattr(c, "label", None) == "Descuento máximo (%)")
    assert campo_descuento.value == "35"
    campo_dias = next(
        c for c in campos if getattr(c, "label", None) == "Días de crédito por defecto"
    )
    assert campo_dias.value == "45"


def test_guardar_llama_al_servicio_con_valores_convertidos(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)
    servicio_falso = MagicMock()
    ctx.services["settings"] = servicio_falso
    servicio_falso.get_business.return_value = None

    control = build_operation_settings_view(ctx)
    campos = _todos_los_controles(control)
    campo_descuento = next(c for c in campos if getattr(c, "label", None) == "Descuento máximo (%)")
    campo_descuento.value = "20"
    boton = _buscar_boton(control, "Guardar")

    boton.on_click(_evento_falso(boton))

    assert servicio_falso.update_operation_settings.called
    actor_llamado, datos = servicio_falso.update_operation_settings.call_args[0]
    assert actor_llamado is admin_actor
    assert datos.max_discount_percent == Decimal("0.20")


def test_guardar_con_descuento_invalido_muestra_error_sin_lanzar(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_operation_settings_view(ctx)
    campos = _todos_los_controles(control)
    campo_descuento = next(c for c in campos if getattr(c, "label", None) == "Descuento máximo (%)")
    campo_descuento.value = "150"
    boton = _buscar_boton(control, "Guardar")

    boton.on_click(_evento_falso(boton))

    mensaje = next(
        c
        for c in _todos_los_controles(control)
        if isinstance(c, ft.Text) and c.value and "descuento" in c.value.lower()
    )
    assert mensaje is not None


def _evento_falso(control: ft.Control) -> ft.Event[ft.Control]:
    return MagicMock(control=control)


def _todos_los_controles(control: ft.Control) -> list:
    """Recorre recursivamente `controls` para obtener una lista plana de sub-controles."""
    encontrados = [control]
    hijos = getattr(control, "controls", None)
    if hijos:
        for hijo in hijos:
            encontrados.extend(_todos_los_controles(hijo))
    return encontrados


def _buscar_boton(control: ft.Control, texto: str) -> ft.Control:
    for candidato in _todos_los_controles(control):
        if getattr(candidato, "content", None) == texto:
            return candidato
    raise AssertionError(f"no se encontró el botón {texto!r}")
