"""Pantalla real de Respaldos: historial, crear, verificar y restaurar en ensayo (T6.1)."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import flet as ft

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_UMBRAL_RECORDATORIO = timedelta(hours=24)


def _recordatorio_respaldo(ultimo: datetime | None, ahora: datetime) -> ft.Control | None:
    """Banner de advertencia si no hay respaldo verificado o el último tiene más de 24 h."""
    if ultimo is not None and ahora - ultimo < _UMBRAL_RECORDATORIO:
        return None

    mensaje = (
        "Todavía no hay un respaldo verificado registrado."
        if ultimo is None
        else (
            f"El último respaldo verificado fue el {ultimo:%Y-%m-%d %H:%M} (hace más de 24 horas)."
        )
    )
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.WARNING_AMBER, color=theme.WARNING),
                ft.Text(mensaje, color=theme.WARNING, expand=True),
            ],
            spacing=theme.SPACING["sm"],
        ),
        bgcolor=ft.Colors.with_opacity(0.1, theme.WARNING),
        border=ft.Border.all(1, theme.WARNING),
        border_radius=ft.BorderRadius.all(theme.RADIUS),
        padding=ft.Padding.all(theme.SPACING["md"]),
    )


def _fila_historial(
    backups_service: Any,
    actor: Any,
    registro: Any,
    mostrar_mensaje: Any,
) -> ft.DataRow:
    verificado = (
        ft.Icon(ft.Icons.CHECK_CIRCLE, color=theme.SUCCESS)
        if registro.verified
        else ft.Icon(ft.Icons.CANCEL, color=theme.ERROR)
    )

    def _verificar(_: ft.Event[ft.Control]) -> None:
        try:
            backups_service.verify(actor, Path(registro.path))
            mostrar_mensaje("Respaldo verificado.", theme.SUCCESS)
        except SistemasHNError as exc:
            mostrar_mensaje(str(exc), theme.ERROR)

    def _restaurar(ruta_ensayo: Path) -> None:
        try:
            backups_service.restore_to_trial(actor, Path(registro.path), ruta_ensayo)
            mostrar_mensaje("Respaldo restaurado en la carpeta de ensayo.", theme.SUCCESS)
        except SistemasHNError as exc:
            mostrar_mensaje(str(exc), theme.ERROR)

    boton_verificar = widgets.secondary_button("Verificar", _verificar, icon=ft.Icons.FACT_CHECK)
    selector_ensayo = widgets.directory_picker(
        _restaurar,
        button_label="Restaurar en ensayo",
        dialog_title="Elegir carpeta de ensayo",
        icon=ft.Icons.RESTORE,
    )

    return ft.DataRow(
        cells=[
            ft.DataCell(ft.Text(f"{registro.created_at:%Y-%m-%d %H:%M}")),
            ft.DataCell(ft.Text(registro.path)),
            ft.DataCell(verificado),
            ft.DataCell(
                ft.Row(controls=[boton_verificar, selector_ensayo], spacing=theme.SPACING["sm"])
            ),
        ]
    )


def build_backups_view(ctx: AppContext) -> ft.Control:
    backups_service = ctx.service("backups")
    actor = ctx.actor
    ahora = ctx.clock() if ctx.clock is not None else datetime.now(UTC)

    ultimo = backups_service.last_verified_at(actor)
    historial = backups_service.history(actor)

    mensaje = ft.Text("")

    def _mostrar_mensaje(texto: str, color: str) -> None:
        mensaje.value = texto
        mensaje.color = color
        with contextlib.suppress(RuntimeError):
            mensaje.update()

    if historial:
        tabla: ft.Control = ft.DataTable(
            columns=[
                ft.DataColumn(label=ft.Text("Fecha")),
                ft.DataColumn(label=ft.Text("Destino")),
                ft.DataColumn(label=ft.Text("Verificado")),
                ft.DataColumn(label=ft.Text("Acciones")),
            ],
            rows=[
                _fila_historial(backups_service, actor, registro, _mostrar_mensaje)
                for registro in historial
            ],
        )
    else:
        tabla = widgets.empty_state("Todavía no hay respaldos registrados.", icon=ft.Icons.BACKUP)

    def _al_elegir_destino(ruta: Path) -> None:
        try:
            backups_service.create(actor, ruta)
            _mostrar_mensaje("Respaldo creado correctamente.", theme.SUCCESS)
        except SistemasHNError as exc:
            _mostrar_mensaje(str(exc), theme.ERROR)

    selector_destino = widgets.directory_picker(
        _al_elegir_destino,
        button_label="Respaldar ahora",
        dialog_title="Elegir carpeta de destino",
        icon=ft.Icons.BACKUP,
    )

    controles: list[ft.Control] = [widgets.page_header("Respaldos")]
    recordatorio = _recordatorio_respaldo(ultimo, ahora)
    if recordatorio is not None:
        controles.append(recordatorio)
    controles.extend([selector_destino, tabla, mensaje])

    return ft.Column(
        controls=controles,
        spacing=theme.SPACING["md"],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
