"""Pantalla "Ajustes de operación": políticas de caja, ventas, crédito y POS (T7.6)."""

from __future__ import annotations

import contextlib
from decimal import Decimal, InvalidOperation

import flet as ft
from pydantic import ValidationError as PydanticValidationError

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.settings.schemas import OperationSettingsInput
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_ETIQUETAS_POLITICA_IMPRESION = {
    "auto": "Imprimir siempre",
    "ask": "Preguntar cada vez",
    "never": "Nunca imprimir",
}


def _texto_ayuda(mensaje: str) -> ft.Text:
    return ft.Text(mensaje, size=theme.FONT_BODY, color=theme.TEXT_MUTED)


def _seccion(titulo: str, controles: list[ft.Control]) -> ft.Control:
    return ft.Column(
        controls=[
            ft.Text(titulo, size=theme.FONT_SUBTITLE, weight=ft.FontWeight.W_600),
            *controles,
        ],
        spacing=theme.SPACING["sm"],
    )


def build_operation_settings_view(ctx: AppContext) -> ft.Control:
    settings_service = ctx.service("settings")

    negocio = settings_service.get_business()

    if negocio is not None:
        valores = OperationSettingsInput(
            cash_session_required=negocio.cash_session_required,
            block_sale_without_stock=negocio.block_sale_without_stock,
            print_receipt_policy=negocio.print_receipt_policy,
            cashier_sees_own_sales_total=negocio.cashier_sees_own_sales_total,
            max_discount_percent=negocio.max_discount_percent,
            default_credit_days=negocio.default_credit_days,
            default_quote_validity_days=negocio.default_quote_validity_days,
            pos_simplified_mode_enabled=negocio.pos_simplified_mode_enabled,
            pos_exit_requires_manager_auth=negocio.pos_exit_requires_manager_auth,
            show_logo_in_app=negocio.show_logo_in_app,
        )
    else:
        valores = OperationSettingsInput()

    campo_caja_requerida = ft.Checkbox(
        label="Exigir caja abierta para vender", value=valores.cash_session_required
    )
    campo_bloquear_sin_stock = ft.Checkbox(
        label="Bloquear ventas sin existencia", value=valores.block_sale_without_stock
    )
    campo_cajero_ve_totales = ft.Checkbox(
        label="El cajero puede ver el total de sus ventas del día",
        value=valores.cashier_sees_own_sales_total,
    )

    campo_politica_impresion = ft.Dropdown(
        label="Impresión de recibos",
        value=valores.print_receipt_policy,
        options=[
            ft.DropdownOption(key=clave, text=texto)
            for clave, texto in _ETIQUETAS_POLITICA_IMPRESION.items()
        ],
    )

    descuento_porcentaje = f"{valores.max_discount_percent * 100:f}".rstrip("0").rstrip(".")
    campo_descuento_max = widgets.form_field(
        "Descuento máximo (%)", value=descuento_porcentaje or "0"
    )
    campo_dias_credito = widgets.form_field(
        "Días de crédito por defecto", value=str(valores.default_credit_days)
    )
    campo_dias_cotizacion = widgets.form_field(
        "Vigencia de cotizaciones (días)", value=str(valores.default_quote_validity_days)
    )

    campo_pos_simplificado = ft.Checkbox(
        label="Activar modo mostrador (POS simplificado)",
        value=valores.pos_simplified_mode_enabled,
    )
    campo_pos_requiere_autorizacion = ft.Checkbox(
        label="Pedir autorización de gerente para salir del modo mostrador",
        value=valores.pos_exit_requires_manager_auth,
    )

    campo_mostrar_logo = ft.Checkbox(
        label="Mostrar el logo del negocio en la barra lateral", value=valores.show_logo_in_app
    )

    mensaje = ft.Text("")

    def _leer_entero(campo: ft.TextField, nombre: str) -> int:
        try:
            return int((campo.value or "").strip())
        except ValueError as exc:
            raise ValueError(f"{nombre} debe ser un número entero") from exc

    def _guardar(_: ft.Event[ft.Control]) -> None:
        try:
            texto_descuento = (campo_descuento_max.value or "").strip()
            try:
                descuento_porcentaje = Decimal(texto_descuento)
            except InvalidOperation as exc:
                raise ValueError("el descuento máximo debe ser un número") from exc
            if descuento_porcentaje < 0 or descuento_porcentaje > 100:
                raise ValueError("el descuento máximo debe estar entre 0 y 100")

            data = OperationSettingsInput(
                cash_session_required=bool(campo_caja_requerida.value),
                block_sale_without_stock=bool(campo_bloquear_sin_stock.value),
                print_receipt_policy=campo_politica_impresion.value or "auto",
                cashier_sees_own_sales_total=bool(campo_cajero_ve_totales.value),
                max_discount_percent=descuento_porcentaje / Decimal(100),
                default_credit_days=_leer_entero(campo_dias_credito, "los días de crédito"),
                default_quote_validity_days=_leer_entero(
                    campo_dias_cotizacion, "la vigencia de cotizaciones"
                ),
                pos_simplified_mode_enabled=bool(campo_pos_simplificado.value),
                pos_exit_requires_manager_auth=bool(campo_pos_requiere_autorizacion.value),
                show_logo_in_app=bool(campo_mostrar_logo.value),
            )
            settings_service.update_operation_settings(ctx.actor, data)
            mensaje.value = "Ajustes guardados."
            mensaje.color = theme.SUCCESS
        except (SistemasHNError, PydanticValidationError, ValueError) as exc:
            mensaje.value = str(exc)
            mensaje.color = theme.ERROR
        with contextlib.suppress(RuntimeError):
            mensaje.update()

    formulario = ft.Column(
        controls=[
            _seccion(
                "Caja y ventas",
                [
                    campo_caja_requerida,
                    _texto_ayuda(
                        "Exigir una caja abierta antes de registrar una venta o cobro en efectivo"
                    ),
                    campo_bloquear_sin_stock,
                    _texto_ayuda(
                        "Impedir vender productos sin existencia disponible; si se desactiva, "
                        "la venta se registra igual y queda marcada como pendiente de entrega"
                    ),
                    campo_cajero_ve_totales,
                    _texto_ayuda("El cajero puede ver el total de sus propias ventas del día"),
                ],
            ),
            ft.Divider(),
            _seccion("Recibos", [campo_politica_impresion]),
            ft.Divider(),
            _seccion(
                "Crédito y descuentos",
                [campo_descuento_max, campo_dias_credito, campo_dias_cotizacion],
            ),
            ft.Divider(),
            _seccion(
                "Punto de venta",
                [
                    campo_pos_simplificado,
                    _texto_ayuda(
                        "En modo mostrador la pantalla de venta se simplifica para agilizar el "
                        "cobro"
                    ),
                    campo_pos_requiere_autorizacion,
                    _texto_ayuda(
                        "Pide la contraseña de un gerente antes de salir del modo mostrador"
                    ),
                ],
            ),
            ft.Divider(),
            _seccion("Apariencia", [campo_mostrar_logo]),
            widgets.primary_button("Guardar", _guardar),
            mensaje,
        ],
        spacing=theme.SPACING["sm"],
    )

    return ft.Column(
        controls=[widgets.page_header("Ajustes de operación"), formulario],
        spacing=theme.SPACING["md"],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
