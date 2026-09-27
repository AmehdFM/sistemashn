"""Pruebas de la pantalla real de Respaldos: historial, recordatorio y acción Verificar."""

from unittest.mock import MagicMock

import flet as ft
from tests.core.ui.views.conftest import contiene_texto

from sistemashn.core.ui.views.backups_view import build_backups_view


def test_build_backups_view_sin_respaldos_muestra_recordatorio(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_backups_view(ctx)

    assert isinstance(control, ft.Control)
    assert contiene_texto(control, "Todavía no hay un respaldo verificado registrado.")
    assert contiene_texto(control, "Todavía no hay respaldos registrados.")


def test_build_backups_view_tras_crear_respaldo_oculta_recordatorio(
    ctx_factory, admin_actor, tmp_path
):
    ctx = ctx_factory(admin_actor)
    destino = tmp_path / "destino"
    destino.mkdir()
    ctx.service("backups").create(admin_actor, destino)

    control = build_backups_view(ctx)

    assert not contiene_texto(control, "Todavía no hay un respaldo verificado registrado.")
    assert not contiene_texto(control, "hace más de 24 horas")


def test_build_backups_view_lista_historial_con_destino(ctx_factory, admin_actor, tmp_path):
    ctx = ctx_factory(admin_actor)
    destino = tmp_path / "destino"
    destino.mkdir()
    receipt = ctx.service("backups").create(admin_actor, destino)

    control = build_backups_view(ctx)

    assert contiene_texto(control, str(receipt.destination))


def test_boton_verificar_llama_al_servicio(ctx_factory, admin_actor, tmp_path):
    ctx = ctx_factory(admin_actor)
    destino = tmp_path / "destino"
    destino.mkdir()
    receipt = ctx.service("backups").create(admin_actor, destino)

    servicio_falso = MagicMock(wraps=ctx.service("backups"))
    ctx.services["backups"] = servicio_falso

    control = build_backups_view(ctx)
    boton_verificar = _buscar_boton(control, "Verificar")

    boton_verificar.on_click(MagicMock(control=boton_verificar))

    servicio_falso.verify.assert_called_once_with(admin_actor, receipt.destination)


def _todos_los_controles(control) -> list:
    encontrados = [control]
    hijos = getattr(control, "controls", None)
    if hijos:
        for hijo in hijos:
            encontrados.extend(_todos_los_controles(hijo))
    filas = getattr(control, "rows", None)
    if filas:
        for fila in filas:
            for celda in fila.cells:
                encontrados.extend(_todos_los_controles(celda.content))
    return encontrados


def _buscar_boton(control, texto: str):
    for candidato in _todos_los_controles(control):
        if getattr(candidato, "content", None) == texto:
            return candidato
    raise AssertionError(f"no se encontró el botón {texto!r}")
