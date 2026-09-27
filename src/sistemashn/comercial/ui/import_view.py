"""Pantalla de importación/exportación de catálogo por Excel (T2.6a)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import flet as ft

from sistemashn.comercial.catalogo.excel import ExcelImportService, ImportPreview
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_POLITICAS = (("solo_validas", "Solo filas válidas"), ("todo_o_nada", "Todo o nada"))


def _plantilla_path(ctx: AppContext) -> Path:
    base = ctx.data_dir or Path(".")
    return base / "plantillas" / "plantilla-productos.xlsx"


def _exportacion_path(ctx: AppContext) -> Path:
    base = ctx.data_dir or Path(".")
    nombre = f"catalogo-{datetime.now():%Y%m%d-%H%M}.xlsx"
    return base / "exportaciones" / nombre


def build_import_view(ctx: AppContext) -> ft.Control:
    excel: ExcelImportService = ctx.service("excel")

    ruta_elegida: dict[str, Path | None] = {"ruta": None}
    selector_archivo = widgets.file_picker(
        lambda ruta: ruta_elegida.__setitem__("ruta", ruta),
        button_label="Elegir archivo .xlsx...",
        dialog_title="Seleccionar catálogo a importar",
        file_type=ft.FilePickerFileType.CUSTOM,
        allowed_extensions=["xlsx"],
    )
    campo_politica = ft.Dropdown(
        label="Política de importación",
        value="solo_validas",
        options=[ft.DropdownOption(key=v, text=t) for v, t in _POLITICAS],
    )
    mensaje = ft.Text("")
    error = ft.Text("", color=theme.ERROR)
    resultado_area = ft.Column(spacing=theme.SPACING["sm"])

    estado: dict[str, ImportPreview | None] = {"preview": None}

    def _actualizar() -> None:
        if mensaje.page is not None:
            mensaje.update()
        if error.page is not None:
            error.update()
        if resultado_area.page is not None:
            resultado_area.update()

    def _descargar_plantilla(_: ft.Event[ft.Control]) -> None:
        error.value = ""
        try:
            destino = _plantilla_path(ctx)
            destino.parent.mkdir(parents=True, exist_ok=True)
            excel.write_template(destino)
            mensaje.value = f"Plantilla guardada en: {destino}"
        except SistemasHNError as exc:
            mensaje.value = ""
            error.value = str(exc)
        _actualizar()

    def _abrir_carpeta_plantilla(_: ft.Event[ft.Control]) -> None:
        destino = _plantilla_path(ctx).parent
        if destino.exists() and os.name == "nt":
            os.startfile(destino)

    def _vista_previa(_: ft.Event[ft.Control]) -> None:
        error.value = ""
        estado["preview"] = None
        ruta = ruta_elegida["ruta"]
        if ruta is None:
            error.value = "elija el archivo a importar"
            resultado_area.controls = []
            _actualizar()
            return
        try:
            preview = excel.preview(ctx.actor, str(ruta))
        except SistemasHNError as exc:
            error.value = str(exc)
            resultado_area.controls = []
            _actualizar()
            return
        estado["preview"] = preview
        resultado_area.controls = _render_preview(preview)
        _actualizar()

    def _confirmar_importacion(_: ft.Event[ft.Control]) -> None:
        error.value = ""
        preview = estado["preview"]
        if preview is None:
            error.value = "genere una vista previa antes de confirmar"
            _actualizar()
            return
        try:
            resultado = excel.commit(
                ctx.actor, preview, policy=campo_politica.value or "solo_validas"
            )
        except SistemasHNError as exc:
            error.value = str(exc)
            _actualizar()
            return
        mensaje.value = (
            f"Importación completada: {resultado.created} creados, "
            f"{resultado.updated} actualizados, {resultado.skipped} omitidos."
        )
        estado["preview"] = None
        resultado_area.controls = []
        _actualizar()

    def _exportar(_: ft.Event[ft.Control]) -> None:
        error.value = ""
        try:
            destino = _exportacion_path(ctx)
            destino.parent.mkdir(parents=True, exist_ok=True)
            excel.export_products(ctx.actor, destino)
            mensaje.value = f"Catálogo exportado a: {destino}"
        except SistemasHNError as exc:
            mensaje.value = ""
            error.value = str(exc)
        _actualizar()

    def _render_preview(preview: ImportPreview) -> list[ft.Control]:
        nuevos = sum(1 for r in preview.rows if r.action == "crear")
        actualizados = sum(1 for r in preview.rows if r.action == "actualizar")
        resumen = ft.Text(
            f"Filas válidas: {len(preview.rows)} de {preview.total_rows} "
            f"({nuevos} nuevos, {actualizados} actualizados, {len(preview.errors)} con error)"
        )
        controles: list[ft.Control] = [resumen]
        if preview.errors:
            columnas = ["Fila", "Columna", "Mensaje"]
            filas = [
                [ft.Text(str(e.row_number)), ft.Text(e.column), ft.Text(e.message)]
                for e in preview.errors
            ]
            tabla = ft.DataTable(
                columns=[ft.DataColumn(label=ft.Text(c)) for c in columnas],
                rows=[ft.DataRow(cells=[ft.DataCell(c) for c in fila]) for fila in filas],
            )
            controles.append(tabla)
        controles.append(widgets.primary_button("Confirmar importación", _confirmar_importacion))
        return controles

    return ft.Column(
        controls=[
            widgets.page_header("Importar catálogo"),
            ft.Row(
                controls=[
                    widgets.secondary_button("Descargar plantilla", _descargar_plantilla),
                    widgets.secondary_button(
                        "Abrir carpeta de plantillas", _abrir_carpeta_plantilla
                    ),
                    widgets.secondary_button("Exportar catálogo", _exportar),
                ],
                spacing=theme.SPACING["sm"],
                wrap=True,
            ),
            mensaje,
            ft.Divider(),
            ft.Row(
                controls=[
                    selector_archivo,
                    campo_politica,
                    widgets.primary_button("Vista previa", _vista_previa),
                ],
                spacing=theme.SPACING["sm"],
                wrap=True,
            ),
            error,
            resultado_area,
        ],
        spacing=theme.SPACING["md"],
        expand=True,
    )
