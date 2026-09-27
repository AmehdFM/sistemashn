"""Pantalla de ajustes del negocio: datos, logo y códigos de recuperación (T1.6b-2)."""

from __future__ import annotations

from pathlib import Path

import flet as ft
from pydantic import ValidationError as PydanticValidationError

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.settings.schemas import BusinessInput
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_business_view(ctx: AppContext) -> ft.Control:
    settings_service = ctx.service("settings")
    recovery_service = ctx.service("recovery")

    negocio = settings_service.get_business()

    campo_nombre = widgets.form_field("Nombre comercial", value=negocio.name if negocio else "")
    campo_razon = widgets.form_field("Razón social", value=negocio.legal_name if negocio else "")
    campo_rtn = widgets.form_field("RTN (14 dígitos)", value=(negocio.rtn or "") if negocio else "")
    campo_direccion = widgets.form_field("Dirección", value=negocio.address if negocio else "")
    campo_telefono = widgets.form_field("Teléfono", value=negocio.phone if negocio else "")
    campo_correo = widgets.form_field("Correo", value=negocio.email if negocio else "")
    campo_isv = ft.Checkbox(
        label="Los precios incluyen ISV",
        value=negocio.prices_include_isv if negocio else True,
    )
    campo_logo = widgets.form_field("Ruta del archivo del logo (PNG/JPG)")

    mensaje = ft.Text("")
    codigos_texto = ft.Text("", selectable=True)

    def _guardar(_: ft.Event[ft.Control]) -> None:
        try:
            data = BusinessInput(
                name=campo_nombre.value or "",
                legal_name=campo_razon.value or "",
                rtn=(campo_rtn.value or "").strip() or None,
                address=campo_direccion.value or "",
                phone=campo_telefono.value or "",
                email=campo_correo.value or "",
                prices_include_isv=bool(campo_isv.value),
            )
            settings_service.update_business(ctx.actor, data)
            mensaje.value = "Datos guardados."
            mensaje.color = theme.SUCCESS
        except (SistemasHNError, PydanticValidationError) as exc:
            mensaje.value = str(exc)
            mensaje.color = theme.ERROR
        mensaje.update()

    def _cambiar_logo(_: ft.Event[ft.Control]) -> None:
        try:
            settings_service.set_logo(ctx.actor, Path(campo_logo.value or ""))
            mensaje.value = "Logo actualizado."
            mensaje.color = theme.SUCCESS
        except (SistemasHNError, OSError) as exc:
            mensaje.value = f"No se pudo actualizar el logo: {exc}"
            mensaje.color = theme.ERROR
        mensaje.update()

    def _regenerar_codigos(_: ft.Event[ft.Control]) -> None:
        try:
            codigos = recovery_service.regenerate_codes(ctx.actor)
            codigos_texto.value = "\n".join(codigos)
            codigos_texto.color = theme.TEXT
        except SistemasHNError as exc:
            codigos_texto.value = f"Error: {exc}"
            codigos_texto.color = theme.ERROR
        codigos_texto.update()

    formulario = ft.Column(
        controls=[
            campo_nombre,
            campo_razon,
            campo_rtn,
            campo_direccion,
            campo_telefono,
            campo_correo,
            campo_isv,
            widgets.primary_button("Guardar", _guardar),
            mensaje,
            ft.Divider(),
            ft.Text("Logo", weight=ft.FontWeight.BOLD),
            campo_logo,
            widgets.secondary_button("Cambiar logo", _cambiar_logo),
        ],
        spacing=theme.SPACING["sm"],
    )

    secciones: list[ft.Control] = [widgets.page_header("Ajustes del negocio"), formulario]

    if ctx.actor is not None and ctx.actor.is_admin:
        secciones.extend(
            [
                ft.Divider(),
                ft.Text("Códigos de recuperación", weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Regenerar invalida los códigos anteriores. Anótelos: solo se "
                    "muestran una vez.",
                    color=theme.TEXT_MUTED,
                ),
                widgets.secondary_button("Regenerar códigos", _regenerar_codigos),
                codigos_texto,
            ]
        )

    return ft.Column(
        controls=secciones,
        spacing=theme.SPACING["md"],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
