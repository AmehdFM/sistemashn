"""Datos técnicos y empaques dentro de la ficha comercial de producto."""

from __future__ import annotations

import contextlib
from decimal import Decimal, InvalidOperation

import flet as ft

from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_FAMILIES = (
    ("fijaciones", "Fijaciones"),
    ("electrico", "Eléctrico"),
    ("plomeria", "Plomería"),
    ("pintura", "Pintura y adhesivos"),
    ("herramientas", "Herramientas"),
    ("construccion", "Construcción"),
    ("otros", "Otros"),
)


def _optional_decimal(value: str | None) -> Decimal | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("El precio debe ser un número válido") from exc


class ItemFormExtension:
    """Sección propia de Ferretería; stock y precios base siguen en Comercial."""

    title = "Datos de ferretería"

    def is_visible(self, ctx: AppContext) -> bool:
        if ctx.actor is None:
            return False
        with session_scope(ctx.session_factory, readonly=True) as session:
            return ctx.authorizer.can(session, ctx.actor, "com.catalogo.ver")

    def build(self, ctx: AppContext, product_id: int) -> ft.Control:
        service = ctx.service("fer_catalog")
        with session_scope(ctx.session_factory, readonly=True) as session:
            can_manage = ctx.authorizer.can(session, ctx.actor, "fer.catalogo.gestionar")

        item = service.get_item(ctx.actor, product_id)
        brand = widgets.form_field("Marca", value=getattr(item, "brand", None) or "")
        family = ft.Dropdown(
            label="Familia",
            value=getattr(item, "family", None) or "otros",
            options=[ft.DropdownOption(key=key, text=label) for key, label in _FAMILIES],
        )
        specs = widgets.form_field(
            "Especificación técnica",
            value=getattr(item, "specs", None) or "",
        )
        specs.hint_text = "Ej.: M8 × 30 mm, acero zincado"
        error = ft.Text("", color=theme.ERROR)
        feedback = ft.Text("", color=theme.TEXT_MUTED)
        packs_column = ft.Column(spacing=theme.SPACING["xs"])

        def _toggle_pack(pack_id: int, active: bool) -> None:
            try:
                service.set_pack_active(ctx.actor, pack_id, active)
            except SistemasHNError as exc:
                _set_message(str(exc), failed=True)
                return
            _set_message("Presentación activada." if active else "Presentación desactivada.")
            _refresh_packs()

        def _set_message(message: str, *, failed: bool = False) -> None:
            error.value = message if failed else ""
            feedback.value = "" if failed else message
            if error.page is not None:
                error.update()
                feedback.update()

        def _refresh_packs() -> None:
            try:
                packs = service.list_packs(ctx.actor, product_id, include_inactive=True)
            except SistemasHNError as exc:
                packs_column.controls = [widgets.error_banner(str(exc))]
            else:
                packs_column.controls = (
                    [
                        ft.Row(
                            controls=[
                                ft.Text(pack.label, weight=ft.FontWeight.W_600, expand=True),
                                ft.Text(f"× {pack.factor_base} unidades base"),
                                ft.Text(pack.code or "Sin código", color=theme.TEXT_MUTED),
                                ft.Text(
                                    "Activa" if pack.active else "Inactiva",
                                    color=theme.TEXT_MUTED,
                                ),
                                ft.Text(
                                    "Admite fracción" if pack.permits_fraction else "Entera",
                                    color=theme.TEXT_MUTED,
                                ),
                                ft.Text(
                                    widgets.format_lempiras(pack.price)
                                    if pack.price is not None
                                    else "Precio base",
                                    color=theme.TEXT_MUTED,
                                ),
                                *(
                                    [
                                        widgets.secondary_button(
                                            "Desactivar" if pack.active else "Activar",
                                            lambda e, p=pack: _toggle_pack(p.id, not p.active),
                                        )
                                    ]
                                    if can_manage
                                    else []
                                ),
                            ],
                            spacing=theme.SPACING["sm"],
                            wrap=True,
                        )
                        for pack in packs
                    ]
                    if packs
                    else [ft.Text("Sin presentaciones adicionales.", color=theme.TEXT_MUTED)]
                )
            with contextlib.suppress(RuntimeError):
                packs_column.update()

        def _save_item(_: ft.Event[ft.Control]) -> None:
            try:
                service.set_item(
                    ctx.actor,
                    product_id,
                    brand=(brand.value or "").strip() or None,
                    family=family.value or None,
                    specs=(specs.value or "").strip() or None,
                )
            except SistemasHNError as exc:
                _set_message(str(exc), failed=True)
                return
            _set_message("Datos técnicos guardados.")

        controls: list[ft.Control] = [
            ft.Text("Identidad técnica", size=theme.FONT_SUBTITLE, weight=ft.FontWeight.W_600),
            ft.Text(
                "Variantes de medida, calibre o rosca incompatibles requieren SKU aparte.",
                color=theme.TEXT_MUTED,
            ),
            ft.Row(controls=[brand, family, specs], wrap=True, spacing=theme.SPACING["sm"]),
        ]
        if can_manage:
            controls.append(widgets.primary_button("Guardar datos técnicos", _save_item))
        else:
            brand.read_only = True
            family.disabled = True
            specs.read_only = True
        controls.extend(
            [
                error,
                feedback,
                ft.Text("Presentaciones", size=theme.FONT_SUBTITLE, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Cada factor convierte a la unidad base. Empaques cerrados se venden enteros.",
                    color=theme.TEXT_MUTED,
                ),
                packs_column,
            ]
        )

        if can_manage:
            code = widgets.form_field("Código de empaque")
            code.hint_text = "Opcional"
            label = widgets.form_field("Presentación")
            label.hint_text = "Ej.: caja de 100"
            factor = widgets.form_field("Unidades base por presentación")
            factor.hint_text = "Ej.: 100"
            price = widgets.form_field("Precio de presentación")
            price.hint_text = "Opcional"
            fraction = ft.Checkbox(
                label="Permite fracción",
                value=False,
                label_style=ft.TextStyle(color=theme.TEXT, size=theme.FONT_BODY),
            )

            def _create_pack(_: ft.Event[ft.Control]) -> None:
                try:
                    try:
                        factor_value = Decimal((factor.value or "").strip())
                    except InvalidOperation as exc:
                        raise ValueError("El factor debe ser un número válido") from exc
                    service.create_pack(
                        ctx.actor,
                        product_id,
                        code=(code.value or "").strip() or None,
                        label=(label.value or "").strip(),
                        factor_base=factor_value,
                        permits_fraction=bool(fraction.value),
                        price=_optional_decimal(price.value),
                    )
                except (SistemasHNError, ValueError) as exc:
                    _set_message(str(exc), failed=True)
                    return
                code.value = ""
                label.value = ""
                factor.value = ""
                price.value = ""
                fraction.value = False
                for control in (code, label, factor, price, fraction):
                    if control.page is not None:
                        control.update()
                _set_message("Presentación agregada.")
                _refresh_packs()

            controls.extend(
                [
                    ft.Text("Agregar presentación", weight=ft.FontWeight.W_600),
                    ft.Row(
                        controls=[code, label, factor, price, fraction],
                        wrap=True,
                        spacing=theme.SPACING["sm"],
                    ),
                    widgets.primary_button("Agregar presentación", _create_pack),
                ]
            )

        _refresh_packs()
        return ft.Column(controls=controls, spacing=theme.SPACING["md"])
