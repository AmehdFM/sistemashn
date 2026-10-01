"""Controles compartidos entre pantallas de Comercial: existencias, movimientos y ajustes."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, InvalidOperation

import flet as ft

from sistemashn.comercial.inventario.service import InventoryService, MovementView
from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.pagination import Page
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.views import format_local_datetime

PERMISO_AJUSTAR = "com.inventario.ajustar"


def safe_page(control: ft.Control) -> ft.Page | None:
    """Devuelve `control.page` o `None` si aún no está adjunto (Flet 1.0 lanza en ese caso)."""
    try:
        return control.page
    except RuntimeError:
        return None


def tiene_permiso(ctx: AppContext, code: str) -> bool:
    """Verifica un permiso del actor actual en una sesión de solo lectura."""
    if ctx.actor is None:
        return False
    with session_scope(ctx.session_factory, readonly=True) as session:
        return ctx.authorizer.can(session, ctx.actor, code)


def parse_decimal(text: str, field_name: str) -> Decimal:
    """Convierte texto a `Decimal`; lanza `ValueError` con mensaje legible si falla o está vacío."""
    texto = (text or "").strip().replace(",", "")
    if not texto:
        raise ValueError(f"{field_name} es obligatorio")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} inválido: {text!r}") from exc


def parse_optional_decimal(text: str, field_name: str = "valor") -> Decimal | None:
    """Convierte texto a `Decimal` o `None` si está vacío; lanza `ValueError` si es inválido."""
    texto = (text or "").strip().replace(",", "")
    if not texto:
        return None
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} inválido: {text!r}") from exc


def validate_reason(reason: str) -> str:
    """Recorta y valida el motivo del ajuste (mínimo 5 caracteres); lanza `ValueError`."""
    motivo = (reason or "").strip()
    if len(motivo) < 5:
        raise ValueError("el motivo del ajuste debe tener al menos 5 caracteres")
    return motivo


def _movements_table(
    pagina: Page[MovementView], on_page_change: Callable[[int], None]
) -> ft.Control:
    columnas = ["Fecha", "Tipo", "Físico", "Apartado", "No vendible", "Costo unit.", "Motivo"]
    filas: list[list[ft.Control]] = []
    for movimiento in pagina.items:
        filas.append(
            [
                ft.Text(format_local_datetime(movimiento.occurred_at)),
                ft.Text(movimiento.kind),
                ft.Text(str(movimiento.d_on_hand)),
                ft.Text(str(movimiento.d_reserved)),
                ft.Text(str(movimiento.d_unsellable)),
                ft.Text(
                    widgets.format_lempiras(movimiento.unit_cost)
                    if movimiento.unit_cost is not None
                    else "—"
                ),
                ft.Text(movimiento.reason or "—"),
            ]
        )
    return widgets.paginated_table(columnas, filas, pagina, on_page_change)


def stock_and_movements_section(
    ctx: AppContext,
    product_id: int,
    movements_page: int,
    on_movements_page_change: Callable[[int], None],
) -> ft.Control:
    """Panel de existencias + últimos movimientos (paginado) de un producto."""
    inventory: InventoryService = ctx.service("inventory")

    try:
        stock = inventory.stock(ctx.actor, product_id)
    except SistemasHNError as exc:
        return widgets.error_banner(str(exc))

    filas_stock = [
        ("Físico", str(stock.on_hand)),
        ("Apartado", str(stock.reserved)),
        ("No vendible", str(stock.unsellable)),
        ("Disponible", str(stock.available)),
    ]
    if stock.avg_cost is not None:
        filas_stock.append(("Costo promedio", widgets.format_lempiras(stock.avg_cost)))

    resumen = ft.Row(
        controls=[
            ft.Column(
                controls=[ft.Text(etiqueta, color=theme.TEXT_MUTED), ft.Text(valor, size=18)],
                spacing=2,
            )
            for etiqueta, valor in filas_stock
        ],
        spacing=theme.SPACING["lg"],
        wrap=True,
    )

    controles: list[ft.Control] = [ft.Text("Existencias", weight=ft.FontWeight.BOLD), resumen]

    try:
        pagina_mov = inventory.movements(ctx.actor, product_id, movements_page)
    except SistemasHNError as exc:
        controles.append(widgets.error_banner(str(exc)))
        return ft.Column(controls=controles, spacing=theme.SPACING["sm"])

    controles.append(ft.Text("Últimos movimientos", weight=ft.FontWeight.BOLD))
    if pagina_mov.items:
        controles.append(_movements_table(pagina_mov, on_movements_page_change))
    else:
        controles.append(widgets.empty_state("Sin movimientos registrados."))

    return ft.Column(controls=controles, spacing=theme.SPACING["sm"])


def open_adjust_dialog(
    ctx: AppContext, control: ft.Control, product_id: int, on_saved: Callable[[], None]
) -> None:
    """Abre el diálogo de ajuste de inventario (cantidad +/-, costo opcional, motivo)."""
    inventory: InventoryService = ctx.service("inventory")

    campo_cantidad = widgets.form_field("Cantidad (positiva = entrada, negativa = salida)")
    campo_costo = widgets.form_field("Costo unitario (opcional, solo entradas)")
    campo_motivo = widgets.form_field("Motivo (mínimo 5 caracteres)")
    error = ft.Text("", color=theme.ERROR)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Ajustar inventario"),
        content=ft.Column(controls=[campo_cantidad, campo_costo, campo_motivo, error], tight=True),
    )

    def _cancelar(_: ft.Event[ft.Control]) -> None:
        dialog.open = False
        dialog.update()

    def _guardar(_: ft.Event[ft.Control]) -> None:
        try:
            delta = parse_decimal(campo_cantidad.value or "", "la cantidad")
            costo = parse_optional_decimal(campo_costo.value or "", "el costo unitario")
            motivo = validate_reason(campo_motivo.value or "")
        except ValueError as exc:
            error.value = str(exc)
            error.update()
            return
        try:
            inventory.adjust(ctx.actor, product_id, delta, motivo, unit_cost=costo)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return
        dialog.open = False
        dialog.update()
        on_saved()

    dialog.actions = [
        widgets.secondary_button("Cancelar", _cancelar),
        widgets.primary_button("Guardar", _guardar),
    ]
    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)


def adjust_button(
    ctx: AppContext, product_id: int, on_saved: Callable[[], None]
) -> ft.Control | None:
    """Botón 'Ajustar inventario' visible solo con `com.inventario.ajustar`."""
    if not tiene_permiso(ctx, PERMISO_AJUSTAR):
        return None
    return widgets.secondary_button(
        "Ajustar inventario",
        lambda e: open_adjust_dialog(ctx, e.control, product_id, on_saved),
    )
