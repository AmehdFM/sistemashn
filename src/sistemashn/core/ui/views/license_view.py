"""Pantalla de licencia: datos de la licencia vigente o el motivo si no valida (T1.6b-2)."""

from __future__ import annotations

import flet as ft

from sistemashn.core.db.session import session_scope
from sistemashn.core.licensing.license import LicenseError
from sistemashn.core.setup.models import Installation
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_license_view(ctx: AppContext) -> ft.Control:
    license_service = ctx.service("license")

    with session_scope(ctx.session_factory, readonly=True) as session:
        instalacion = session.get(Installation, 1)

    encabezado = widgets.page_header("Licencia")

    if instalacion is None:
        return ft.Column(
            controls=[encabezado, widgets.error_banner("La instalación aún no se completó.")],
            spacing=theme.SPACING["md"],
        )

    try:
        info = license_service.current(
            expected_vertical=instalacion.vertical,
            installation_id=instalacion.installation_id,
        )
    except LicenseError as exc:
        return ft.Column(
            controls=[
                encabezado,
                widgets.error_banner(f"La licencia no es válida ({exc.reason}): {exc}"),
            ],
            spacing=theme.SPACING["md"],
        )

    if info is None:
        return ft.Column(
            controls=[encabezado, widgets.empty_state("No hay licencia instalada.")],
            spacing=theme.SPACING["md"],
        )

    filas = [
        ("Negocio", info.business_name),
        ("Edición", info.edition),
        ("Identificador de licencia", info.license_id),
        ("Emitida", info.issued_at),
    ]
    tarjeta = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text(etiqueta, size=theme.FONT_BODY, color=theme.TEXT_MUTED, width=200),
                    ft.Text(valor, size=theme.FONT_BODY, selectable=True),
                ],
                wrap=True,
                spacing=theme.SPACING["sm"],
            )
            for etiqueta, valor in filas
        ],
        spacing=theme.SPACING["sm"],
    )

    return ft.Column(controls=[encabezado, tarjeta], spacing=theme.SPACING["md"])
