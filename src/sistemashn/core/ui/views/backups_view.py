"""Pantalla real de Respaldos: historial, crear, verificar, restaurar en ensayo (T6.1)
y aplicar una actualización manual firmada desde un paquete ZIP local (T6.4)."""

from __future__ import annotations

import contextlib
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import flet as ft

from sistemashn import __version__
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.operations.probe_update import InvalidPackageError, validate_package
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.updater.package import verify_signature

_UMBRAL_RECORDATORIO = timedelta(hours=24)


def _instalacion_actual() -> Path:
    """Carpeta de instalación del programa en ejecución.

    Empaquetado (PyInstaller/`flet build`): la carpeta del ejecutable. En desarrollo
    (sin empaquetar) no hay una instalación real que reemplazar — este valor solo
    importa cuando de verdad se aplica una actualización, algo que solo tiene sentido
    probar en un build de Windows real (ver docs/superpowers/plans/fase-6-operacion-entrega.md).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(sys.argv[0]).resolve().parent


def build_updater_command(
    package: Path,
    installation: Path,
    db_path: Path,
    work_dir: Path,
    lock_file: Path,
    *,
    python_executable: str = sys.executable,
) -> list[str]:
    """Arma el comando para invocar el proceso `updater` (T6.3) fuera del proceso de la app.

    En desarrollo se invoca `updater/__main__.py` con el mismo intérprete; en un build
    empaquetado, `installer/sistemashn.iss` instala `updater.exe` junto al programa y
    este comando debería apuntar a él en su lugar (decisión pendiente de ajustar al
    integrar el instalador real, documentada aquí para no perder el enlace).
    """
    return [
        python_executable,
        "-m",
        "sistemashn.updater",
        str(package),
        str(installation),
        str(db_path),
        str(work_dir),
        str(lock_file),
    ]


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


def validate_update_package(
    zip_path: Path,
    installed_version: str,
    *,
    public_keys: dict[str, bytes] | None = None,
) -> Any:
    """Verifica la firma Ed25519 del manifiesto y luego su contenido (T6.2/T6.4).

    Propaga `InvalidPackageError` (o su subclase `InvalidSignatureError`) ante
    cualquier problema, sin tocar disco. Extraído como función independiente de la
    UI para poder probarlo sin construir controles de Flet.
    """
    if public_keys is None:
        verify_signature(zip_path)
    else:
        verify_signature(zip_path, public_keys)
    return validate_package(zip_path, installed_version)


def _seccion_actualizaciones(ctx: AppContext) -> ft.Control:
    """ "Aplicar paquete local (ZIP)" (T6.4): valida firma+manifiesto, muestra un resumen
    y solo tras confirmar cierra la app y lanza el proceso `updater` (T6.3) por separado."""
    resumen = ft.Text("")
    error = ft.Text("", color=theme.ERROR)
    manifest_valido: dict[str, Any] = {}

    def _mostrar_error(texto: str) -> None:
        resumen.value = ""
        error.value = texto
        with contextlib.suppress(RuntimeError):
            resumen.update()
            error.update()

    def _al_elegir_zip(ruta: Path) -> None:
        error.value = ""
        manifest_valido.clear()
        try:
            manifest = validate_update_package(ruta, __version__)
        except InvalidPackageError as exc:
            _mostrar_error(f"Paquete inválido: {exc}")
            return

        manifest_valido["package"] = ruta
        manifest_valido["manifest"] = manifest
        resumen.value = (
            f"Versión actual: {__version__}  →  Nueva versión: {manifest.version}\n"
            f"Revisión de esquema destino: {manifest.schema_revision}\n"
            f"Archivos a reemplazar: {len(manifest.files)}"
        )
        with contextlib.suppress(RuntimeError):
            resumen.update()
            error.update()

    def _aplicar(evento: ft.Event[ft.Control]) -> None:
        if "package" not in manifest_valido:
            return
        ctx_data_dir = ctx.data_dir
        if ctx_data_dir is None:
            _mostrar_error("No se pudo determinar la carpeta de datos de la instalación.")
            return

        db_path = getattr(ctx.service("backups"), "db_path", ctx_data_dir / "sistemashn.db")
        work_dir = ctx_data_dir / "update-work"
        lock_file = ctx_data_dir / ".app.lock"
        comando = build_updater_command(
            manifest_valido["package"],
            _instalacion_actual(),
            Path(db_path),
            work_dir,
            lock_file,
        )
        # Lanza el updater como proceso APARTE y cierra esta app: la app nunca aplica la
        # actualización sobre sí misma (ver T6.3). No hay forma de probar el cierre real de
        # ventana ni el proceso hijo en este entorno de pruebas (requiere un build de
        # Windows real); `build_updater_command` sí está probado de forma aislada.
        subprocess.Popen(comando)
        pagina = evento.control.page
        if pagina is not None:
            pagina.window.close()

    selector_zip = widgets.file_picker(
        _al_elegir_zip,
        button_label="Elegir paquete de actualización (.zip)...",
        allowed_extensions=["zip"],
        icon=ft.Icons.SYSTEM_UPDATE,
    )
    boton_aplicar = widgets.primary_button("Aplicar actualización", _aplicar)

    return ft.Column(
        controls=[
            ft.Text("Actualizaciones", weight=ft.FontWeight.BOLD),
            ft.Text(
                "Buscar actualización por internet: requiere configurar un servidor de "
                "actualizaciones (pendiente, ver T6.5).",
                color=theme.TEXT_MUTED,
            ),
            selector_zip,
            resumen,
            error,
            boton_aplicar,
        ],
        spacing=theme.SPACING["sm"],
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
        tabla: ft.Control = widgets.readable_table(
            ft.DataTable(
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
    controles.extend(
        [selector_destino, tabla, mensaje, ft.Divider(), _seccion_actualizaciones(ctx)]
    )

    return ft.Column(
        controls=controles,
        spacing=theme.SPACING["md"],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
