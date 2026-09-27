"""Pantalla de inicio de sesión y recuperación de acceso del administrador (T1.6b-1)."""

from __future__ import annotations

import contextlib
from collections.abc import Callable

import flet as ft

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_CARD_WIDTH = 380


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


def build_login_view(ctx: AppContext, on_login: Callable[[Actor], None]) -> ft.Control:
    """Tarjeta centrada con usuario/contraseña y enlace de recuperación del administrador."""
    identity = ctx.service("identity")
    recovery = ctx.service("recovery")

    error_slot = ft.Column(controls=[])
    usuario = widgets.form_field("Usuario", autofocus=True)

    def _set_error(message: str | None) -> None:
        error_slot.controls = [widgets.error_banner(message)] if message else []
        _safe_update(error_slot)

    def _entrar(_: ft.Event[ft.Control]) -> None:
        try:
            actor = identity.login(usuario.value or "", password.value or "")
        except SistemasHNError as exc:
            _set_error(str(exc))
            return
        on_login(actor)

    password = widgets.form_field("Contraseña", password=True, on_submit=_entrar)

    def _abrir_recuperacion(e: ft.Event[ft.Control]) -> None:
        dialogo = _build_recovery_dialog(recovery)
        e.control.page.show_dialog(dialogo)

    encabezado: list[ft.Control] = []
    if ctx.logo_path is not None:
        encabezado.append(ft.Image(src=str(ctx.logo_path), width=64, height=64))
    encabezado.append(
        ft.Text(ctx.business_name, size=20, weight=ft.FontWeight.BOLD, color=theme.TEXT)
    )

    tarjeta = ft.Container(
        width=_CARD_WIDTH,
        bgcolor=theme.SURFACE,
        border=ft.Border.all(1, theme.BORDER),
        border_radius=ft.BorderRadius.all(theme.RADIUS),
        padding=ft.Padding.all(theme.SPACING["xl"]),
        content=ft.Column(
            controls=[
                ft.Column(
                    controls=encabezado,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=theme.SPACING["sm"],
                ),
                error_slot,
                usuario,
                password,
                widgets.primary_button("Iniciar sesión", _entrar),
                ft.TextButton(
                    content="¿Olvidó la contraseña del administrador?",
                    on_click=_abrir_recuperacion,
                ),
            ],
            spacing=theme.SPACING["md"],
        ),
    )

    return ft.Container(
        content=tarjeta,
        alignment=ft.Alignment.CENTER,
        bgcolor=theme.CONTENT_BG,
        expand=True,
    )


def _build_recovery_dialog(recovery: object) -> ft.AlertDialog:
    error_slot = ft.Column(controls=[])
    exito_slot = ft.Column(controls=[])

    def _set_error(message: str | None) -> None:
        error_slot.controls = [widgets.error_banner(message)] if message else []
        _safe_update(error_slot)

    def _set_exito(message: str | None) -> None:
        exito_slot.controls = [ft.Text(message, color=theme.SUCCESS)] if message else []
        _safe_update(exito_slot)

    # Opción A: código de recuperación local
    codigo = widgets.form_field("Código de recuperación (XXXX-XXXX-XXXX)")
    nueva_a = widgets.form_field("Nueva contraseña", password=True)

    def _recuperar_con_codigo(_: ft.Event[ft.Control]) -> None:
        try:
            recovery.recover_with_code(codigo.value or "", nueva_a.value or "")
        except SistemasHNError as exc:
            _set_error(str(exc))
            return
        _set_error(None)
        _set_exito("Contraseña restablecida. Ya puede iniciar sesión.")

    # Opción B: autorización asistida del vendedor
    desafio = recovery.create_challenge()
    campo_desafio = ft.TextField(
        label="Desafío (envíelo a soporte)", value=desafio, read_only=True, multiline=True
    )
    token = widgets.form_field("Token de autorización del vendedor")
    nueva_b = widgets.form_field("Nueva contraseña", password=True)

    def _recuperar_con_token(_: ft.Event[ft.Control]) -> None:
        try:
            recovery.recover_with_vendor_token(token.value or "", nueva_b.value or "")
        except SistemasHNError as exc:
            _set_error(str(exc))
            return
        _set_error(None)
        _set_exito("Contraseña restablecida. Ya puede iniciar sesión.")

    contenido = ft.Column(
        controls=[
            error_slot,
            exito_slot,
            ft.Text("Con código de recuperación", weight=ft.FontWeight.BOLD),
            codigo,
            nueva_a,
            widgets.primary_button("Restablecer con código", _recuperar_con_codigo),
            ft.Divider(),
            ft.Text("Con soporte del proveedor", weight=ft.FontWeight.BOLD),
            campo_desafio,
            _copy_button("Copiar desafío", desafio),
            token,
            nueva_b,
            widgets.primary_button("Restablecer con token", _recuperar_con_token),
        ],
        spacing=theme.SPACING["sm"],
        scroll=ft.ScrollMode.AUTO,
        tight=True,
    )

    dialogo = ft.AlertDialog(
        modal=True,
        title=ft.Text("Recuperar acceso del administrador"),
        content=ft.Container(content=contenido, width=420, height=480),
    )

    def _cerrar(_: ft.Event[ft.Control]) -> None:
        dialogo.open = False
        dialogo.update()

    dialogo.actions = [widgets.secondary_button("Cerrar", _cerrar)]
    return dialogo
