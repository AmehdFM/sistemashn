"""Resumen operativo de la ferretería a partir de reportes compartidos."""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone

import flet as ft

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_HONDURAS = timezone(timedelta(hours=-6))


def _period_start(now: datetime, period: str) -> datetime:
    local = now.astimezone(_HONDURAS)
    if period == "semana":
        day = local.date() - timedelta(days=6)
    elif period == "mes":
        day = local.date().replace(day=1)
    else:
        day = local.date()
    return datetime(day.year, day.month, day.day, tzinfo=_HONDURAS).astimezone(now.tzinfo)


def build_summary_view(ctx: AppContext) -> ft.Control:
    reports = ctx.service("reports")
    period = ft.Dropdown(
        label="Período",
        value="hoy",
        options=[
            ft.DropdownOption(key="hoy", text="Hoy"),
            ft.DropdownOption(key="semana", text="Últimos 7 días"),
            ft.DropdownOption(key="mes", text="Mes actual"),
        ],
    )
    output = ft.Column(spacing=theme.SPACING["md"])
    error = ft.Text("", color=theme.ERROR)

    def _metric(label: str, value: str) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(label, color=theme.TEXT_MUTED, size=theme.FONT_BODY),
                    ft.Text(value, size=theme.FONT_SUBTITLE, weight=ft.FontWeight.W_600),
                ],
                spacing=theme.SPACING["xs"],
            ),
            bgcolor=theme.SURFACE,
            padding=ft.Padding.all(theme.SPACING["md"]),
            border_radius=ft.BorderRadius.all(theme.RADIUS),
        )

    def _load(_: ft.Event[ft.Control] | None = None) -> None:
        now = ctx.clock()
        start = _period_start(now, period.value or "hoy")
        try:
            report = reports.sales_and_profit(ctx.actor, start, now)
            low = reports.low_stock(ctx.actor, page=1, page_size=5)
        except SistemasHNError as exc:
            error.value = str(exc)
            output.controls = []
        else:
            error.value = ""
            margin = (
                widgets.format_lempiras(report.total_profit)
                if report.total_profit is not None
                else "Sin cálculo fiable"
            )
            margin_pct = (
                f"{report.total_profit / report.total_sales * 100:.1f} %"
                if report.total_profit is not None and report.total_sales > 0
                else "Sin base de ventas"
            )
            output.controls = [
                ft.Row(
                    controls=[
                        _metric("Venta neta sin ISV", widgets.format_lempiras(report.total_sales)),
                        _metric("Margen bruto", margin),
                        _metric("Margen bruto %", margin_pct),
                        _metric("Artículos bajo mínimo", str(low.total)),
                    ],
                    wrap=True,
                    spacing=theme.SPACING["md"],
                ),
                ft.Text(
                    f"Período: {start.astimezone(_HONDURAS):%d/%m/%Y %H:%M} "
                    f"a {now.astimezone(_HONDURAS):%d/%m/%Y %H:%M} (Honduras)",
                    color=theme.TEXT_MUTED,
                ),
            ]
            notices = []
            if report.incomplete_cost_sales:
                notices.append(
                    f"{report.incomplete_cost_sales} venta(s) sin costo fiable por falta de stock"
                )
            if report.unlinked_returns:
                notices.append(f"{report.unlinked_returns} devolución(es) sin venta vinculada")
            if notices:
                output.controls.append(
                    widgets.error_banner("Estimación incompleta: " + "; ".join(notices))
                )
            output.controls.append(
                ft.Text("Revisar existencias", size=theme.FONT_SUBTITLE, weight=ft.FontWeight.W_600)
            )
            output.controls.extend(
                ft.Text(f"{item.code} · {item.name}: {item.available} disponibles")
                for item in low.items
            )
            if not low.items:
                output.controls.append(
                    ft.Text("Sin artículos bajo mínimo.", color=theme.TEXT_MUTED)
                )
            output.controls.append(
                ft.Text(
                    "Margen bruto operativo; excluye gastos y no representa utilidad neta.",
                    color=theme.TEXT_MUTED,
                )
            )
        with contextlib.suppress(RuntimeError):
            error.update()
            output.update()

    period.on_change = _load
    _load()
    return ft.Column(
        controls=[
            widgets.page_header("Resumen del negocio"),
            period,
            error,
            output,
        ],
        spacing=theme.SPACING["md"],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
