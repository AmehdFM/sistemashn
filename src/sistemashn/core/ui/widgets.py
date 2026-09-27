"""Controles puros y reutilizables de la UI (T1.6a)."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import flet as ft

from sistemashn.core.pagination import Page
from sistemashn.core.ui import theme


def format_lempiras(value: Decimal) -> str:
    """Formatea un monto como `L 1,234.56` (negativo: `-L 5.00`)."""
    negativo = value < 0
    monto = f"L {abs(value):,.2f}"
    return f"-{monto}" if negativo else monto


def money_text(value: Decimal) -> ft.Text:
    """Texto con un monto formateado en lempiras."""
    return ft.Text(format_lempiras(value))


def page_header(
    title: str,
    subtitle: str | None = None,
    actions: list[ft.Control] | None = None,
) -> ft.Control:
    """Encabezado de pantalla: título, subtítulo opcional y acciones a la derecha."""
    textos: list[ft.Control] = [
        ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=theme.TEXT)
    ]
    if subtitle:
        textos.append(ft.Text(subtitle, size=14, color=theme.TEXT_MUTED))

    return ft.Row(
        controls=[
            ft.Column(controls=textos, spacing=2, expand=True),
            ft.Row(controls=actions or [], spacing=theme.SPACING["sm"]),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def empty_state(
    message: str,
    icon: ft.IconData = ft.Icons.INBOX,
    action: ft.Control | None = None,
) -> ft.Control:
    """Estado vacío: icono, mensaje y acción opcional, centrados."""
    controles: list[ft.Control] = [
        ft.Icon(icon, size=48, color=theme.TEXT_MUTED),
        ft.Text(message, color=theme.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
    ]
    if action is not None:
        controles.append(action)
    return ft.Container(
        content=ft.Column(
            controls=controles,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=theme.SPACING["md"],
        ),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.all(theme.SPACING["xl"]),
        expand=True,
    )


def error_banner(message: str) -> ft.Control:
    """Aviso de error en un contenedor con fondo distintivo."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=theme.ERROR),
                ft.Text(message, color=theme.ERROR, expand=True),
            ],
            spacing=theme.SPACING["sm"],
        ),
        bgcolor=ft.Colors.with_opacity(0.1, theme.ERROR),
        border=ft.Border.all(1, theme.ERROR),
        border_radius=ft.BorderRadius.all(theme.RADIUS),
        padding=ft.Padding.all(theme.SPACING["md"]),
    )


def loading(message: str = "Cargando...") -> ft.Control:
    """Indicador de carga centrado con mensaje."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=32, height=32),
                ft.Text(message, color=theme.TEXT_MUTED),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=theme.SPACING["md"],
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )


def forbidden_view() -> ft.Control:
    """Placeholder cuando el actor no tiene permiso para la ruta solicitada."""
    return empty_state("No tiene permiso para ver esta pantalla.", icon=ft.Icons.BLOCK)


def not_found_view() -> ft.Control:
    """Placeholder cuando la ruta solicitada no existe."""
    return empty_state("Pantalla no encontrada.", icon=ft.Icons.SEARCH_OFF)


def confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable[[], None],
    confirm_text: str = "Confirmar",
) -> ft.AlertDialog:
    """Diálogo de confirmación con acciones cancelar/confirmar."""
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
    )

    def _cerrar(_: ft.Event[ft.Control]) -> None:
        dialog.open = False
        dialog.update()

    def _confirmar(_: ft.Event[ft.Control]) -> None:
        dialog.open = False
        dialog.update()
        on_confirm()

    dialog.actions = [
        secondary_button("Cancelar", _cerrar),
        primary_button(confirm_text, _confirmar),
    ]
    return dialog


def paginated_table(
    columns: list[str],
    rows: list[list[ft.Control]],
    page: Page,
    on_page_change: Callable[[int], None],
) -> ft.Control:
    """Tabla con controles anterior/siguiente y resumen `Página X de Y · N registros`."""
    tabla = ft.DataTable(
        columns=[ft.DataColumn(label=ft.Text(nombre)) for nombre in columns],
        rows=[ft.DataRow(cells=[ft.DataCell(control) for control in fila]) for fila in rows],
    )

    puede_retroceder = page.page > 1
    puede_avanzar = page.page < page.pages

    def _anterior(_: ft.Event[ft.Control]) -> None:
        if puede_retroceder:
            on_page_change(page.page - 1)

    def _siguiente(_: ft.Event[ft.Control]) -> None:
        if puede_avanzar:
            on_page_change(page.page + 1)

    resumen = ft.Text(
        f"Página {page.page} de {page.pages} · {page.total} registros",
        color=theme.TEXT_MUTED,
    )

    paginador = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT, on_click=_anterior, disabled=not puede_retroceder
            ),
            resumen,
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT, on_click=_siguiente, disabled=not puede_avanzar
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.Column(controls=[tabla, paginador], spacing=theme.SPACING["sm"])


def form_field(
    label: str,
    *,
    value: str = "",
    password: bool = False,
    autofocus: bool = False,
    on_submit: Callable[[ft.Event[ft.TextField]], None] | None = None,
) -> ft.TextField:
    """Campo de formulario estándar."""
    return ft.TextField(
        label=label,
        value=value,
        password=password,
        can_reveal_password=password,
        autofocus=autofocus,
        on_submit=on_submit,
    )


def primary_button(
    text: str,
    on_click: Callable[[ft.Event[ft.Control]], None],
    icon: ft.IconData | None = None,
) -> ft.Control:
    """Botón de acción principal (color de marca)."""
    return ft.FilledButton(content=text, icon=icon, on_click=on_click)


def secondary_button(
    text: str,
    on_click: Callable[[ft.Event[ft.Control]], None],
    icon: ft.IconData | None = None,
) -> ft.Control:
    """Botón de acción secundaria."""
    return ft.OutlinedButton(content=text, icon=icon, on_click=on_click)


def file_picker(
    on_selected: Callable[[Path], None],
    *,
    button_label: str = "Elegir archivo...",
    dialog_title: str = "Seleccionar archivo",
    file_type: ft.FilePickerFileType = ft.FilePickerFileType.ANY,
    allowed_extensions: list[str] | None = None,
    icon: ft.IconData | None = ft.Icons.ATTACH_FILE,
) -> ft.Control:
    """Botón que abre el selector nativo de archivos del sistema operativo.

    Evita que el usuario tenga que escribir o pegar una ruta a mano (frecuente causa
    de errores: comillas de "Copiar como ruta" de Windows, espacios, rutas relativas).
    Al elegir un archivo llama a `on_selected` con la ruta absoluta reportada por el
    sistema operativo y muestra el nombre elegido junto al botón.
    """
    nombre_elegido = ft.Text("", color=theme.TEXT_MUTED)

    async def _elegir(_: ft.Event[ft.Control]) -> None:
        picker = ft.FilePicker()
        archivos = await picker.pick_files(
            dialog_title=dialog_title,
            file_type=file_type,
            allowed_extensions=allowed_extensions,
        )
        if not archivos or not archivos[0].path:
            return
        ruta = Path(archivos[0].path)
        nombre_elegido.value = ruta.name
        with contextlib.suppress(RuntimeError):
            nombre_elegido.update()
        on_selected(ruta)

    return ft.Row(
        controls=[secondary_button(button_label, _elegir, icon=icon), nombre_elegido],
        spacing=theme.SPACING["sm"],
    )


def image_picker(
    on_selected: Callable[[Path], None],
    *,
    button_label: str = "Elegir imagen...",
    dialog_title: str = "Seleccionar imagen",
) -> ft.Control:
    """Como `file_picker`, pero filtrado a archivos de imagen."""
    return file_picker(
        on_selected,
        button_label=button_label,
        dialog_title=dialog_title,
        file_type=ft.FilePickerFileType.IMAGE,
        icon=ft.Icons.IMAGE,
    )
