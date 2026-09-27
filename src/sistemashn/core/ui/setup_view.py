"""Asistente de primer arranque: licencia, negocio, administrador y recuperación (T1.6b-1)."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from pathlib import Path

import flet as ft

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.licensing.license import LicenseError
from sistemashn.core.settings.schemas import BusinessInput
from sistemashn.core.setup.service import SetupState, SetupStep
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_LICENSE_REASONS = {
    "formato": "El texto de la licencia no tiene el formato esperado.",
    "firma": "La firma de la licencia no es válida.",
    "clave": "La licencia fue firmada con una clave desconocida.",
    "vertical": "Esta licencia no corresponde a este producto.",
    "instalacion": "Esta licencia no corresponde a esta instalación.",
    "maquina": "Esta licencia no corresponde a esta máquina.",
}


def _license_message(exc: LicenseError) -> str:
    return _LICENSE_REASONS.get(exc.reason, str(exc))


def _safe_update(control: ft.Control) -> None:
    """`Control.update()` exige estar montado en una página; no hace nada si aún no lo está."""
    with contextlib.suppress(RuntimeError):
        control.update()


def _copy_button(label: str, text: str) -> ft.Control:
    """Botón que copia `text` al portapapeles (requiere una página activa; ver ADR-004)."""
    try:
        return ft.Button(content=label, action=ft.CopyToClipboard(text))
    except RuntimeError:
        # Sin página activa (p. ej. construcción en pruebas): botón deshabilitado.
        return ft.Button(content=label, disabled=True)


def build_setup_view(ctx: AppContext, on_done: Callable[[], None]) -> ft.Control:
    """Asistente de 4 pasos según `SetupService.state()`; reinicia en el paso donde quedó."""
    setup_service = ctx.service("setup")

    error_slot = ft.Column(controls=[])
    content_slot = ft.Column(controls=[], spacing=theme.SPACING["md"])
    pending_codes: dict[str, list[str]] = {}

    def _set_error(message: str | None) -> None:
        error_slot.controls = [widgets.error_banner(message)] if message else []
        _safe_update(error_slot)

    def _refresh() -> None:
        _set_error(None)
        state = setup_service.state()
        content_slot.controls = [_build_step(state)]
        _safe_update(content_slot)

    def _build_step(state: SetupState) -> ft.Control:
        if state.step == SetupStep.LICENSE:
            return _step_license(state)
        if state.step == SetupStep.BUSINESS:
            return _step_business()
        if state.step == SetupStep.ADMIN:
            return _step_admin()
        if state.step == SetupStep.RECOVERY:
            return _step_recovery()
        on_done()
        return widgets.loading("Configuración completada...")

    def _step_license(state: SetupState) -> ft.Control:
        codigo = state.request_code or ""
        campo_codigo = ft.TextField(
            label="Código de solicitud", value=codigo, read_only=True, multiline=True
        )
        campo_licencia = ft.TextField(
            label="Pegue aquí el texto de la licencia", multiline=True, min_lines=3
        )

        def _enviar(_: ft.Event[ft.Control]) -> None:
            try:
                setup_service.submit_license(campo_licencia.value or "")
            except LicenseError as exc:
                _set_error(_license_message(exc))
                return
            except SistemasHNError as exc:
                _set_error(str(exc))
                return
            _refresh()

        return ft.Column(
            controls=[
                ft.Text("1. Licencia", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Envíe este código a su proveedor y pegue la licencia recibida."),
                campo_codigo,
                _copy_button("Copiar código", codigo),
                campo_licencia,
                widgets.primary_button("Continuar", _enviar),
            ],
            spacing=theme.SPACING["sm"],
        )

    def _step_business() -> ft.Control:
        nombre = widgets.form_field("Nombre comercial")
        razon = widgets.form_field("Razón social")
        rtn = widgets.form_field("RTN (14 dígitos, opcional)")
        direccion = widgets.form_field("Dirección")
        telefono = widgets.form_field("Teléfono")
        correo = widgets.form_field("Correo")
        precios_isv = ft.Checkbox(label="Los precios incluyen ISV", value=True)
        logo_ruta = widgets.form_field("Ruta de archivo del logo (opcional, PNG/JPG)")

        def _enviar(_: ft.Event[ft.Control]) -> None:
            try:
                datos = BusinessInput(
                    name=nombre.value or "",
                    legal_name=razon.value or "",
                    rtn=(rtn.value or "").strip() or None,
                    address=direccion.value or "",
                    phone=telefono.value or "",
                    email=correo.value or "",
                    prices_include_isv=bool(precios_isv.value),
                )
            except ValueError as exc:
                _set_error(str(exc))
                return
            logo = Path(logo_ruta.value) if logo_ruta.value else None
            try:
                setup_service.submit_business(datos, logo)
            except SistemasHNError as exc:
                _set_error(str(exc))
                return
            _refresh()

        return ft.Column(
            controls=[
                ft.Text("2. Datos del negocio", size=18, weight=ft.FontWeight.BOLD),
                nombre,
                razon,
                rtn,
                direccion,
                telefono,
                correo,
                precios_isv,
                logo_ruta,
                widgets.primary_button("Continuar", _enviar),
            ],
            spacing=theme.SPACING["sm"],
        )

    def _step_admin() -> ft.Control:
        usuario = widgets.form_field("Usuario")
        nombre = widgets.form_field("Nombre completo")
        password = widgets.form_field("Contraseña", password=True)
        confirmar = widgets.form_field("Confirmar contraseña", password=True)

        def _enviar(_: ft.Event[ft.Control]) -> None:
            if (password.value or "") != (confirmar.value or ""):
                _set_error("Las contraseñas no coinciden.")
                return
            try:
                codigos = setup_service.create_admin(
                    usuario.value or "", nombre.value or "", password.value or ""
                )
            except SistemasHNError as exc:
                _set_error(str(exc))
                return
            pending_codes["codes"] = codigos
            _refresh()

        return ft.Column(
            controls=[
                ft.Text("3. Administrador", size=18, weight=ft.FontWeight.BOLD),
                usuario,
                nombre,
                password,
                confirmar,
                widgets.primary_button("Continuar", _enviar),
            ],
            spacing=theme.SPACING["sm"],
        )

    def _step_recovery() -> ft.Control:
        codigos = pending_codes.get("codes") or []
        lista = ft.Column(
            controls=[ft.Text(codigo, font_family="Consolas") for codigo in codigos],
            spacing=2,
        )
        confirmado = ft.Checkbox(label="Los guardé en un lugar seguro", value=False)

        def _finalizar(_: ft.Event[ft.Control]) -> None:
            try:
                setup_service.confirm_recovery_codes_saved()
            except SistemasHNError as exc:
                _set_error(str(exc))
                return
            _refresh()

        boton = widgets.primary_button("Finalizar", _finalizar)
        boton.disabled = True

        def _cambiar(_: ft.Event[ft.Control]) -> None:
            boton.disabled = not confirmado.value
            _safe_update(boton)

        confirmado.on_change = _cambiar

        return ft.Column(
            controls=[
                ft.Text("4. Códigos de recuperación", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Anote estos códigos en un lugar seguro: permiten recuperar el acceso "
                    "del administrador si olvida su contraseña. No se mostrarán de nuevo."
                ),
                lista,
                confirmado,
                boton,
            ],
            spacing=theme.SPACING["sm"],
        )

    _refresh()
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Configuración inicial de SistemasHN", size=22, weight=ft.FontWeight.BOLD),
                error_slot,
                content_slot,
            ],
            spacing=theme.SPACING["md"],
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.Padding.all(theme.SPACING["xl"]),
        expand=True,
    )
