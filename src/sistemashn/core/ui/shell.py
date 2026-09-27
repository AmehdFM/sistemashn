"""Cascarón de la aplicación: barra lateral + área de contenido (T1.6a)."""

from __future__ import annotations

from collections.abc import Callable
from itertools import groupby

import flet as ft

from sistemashn.core.ui import theme
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.router import Router

SIDEBAR_WIDTH = 240


def _menu_item(
    ctx: AppContext,
    route: str,
    label: str,
    icon: str,
    active: bool,
    on_navigate: Callable[[str], None],
) -> ft.Control:
    def _click(_: ft.Event[ft.Control]) -> None:
        on_navigate(route)

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    getattr(ft.Icons, icon, ft.Icons.CIRCLE), color=theme.SIDEBAR_TEXT, size=18
                ),
                ft.Text(label, color=theme.SIDEBAR_TEXT),
            ],
            spacing=theme.SPACING["sm"],
        ),
        padding=ft.Padding.symmetric(horizontal=theme.SPACING["md"], vertical=theme.SPACING["sm"]),
        border_radius=ft.BorderRadius.all(theme.RADIUS),
        bgcolor=theme.PRIMARY if active else None,
        on_click=_click,
        ink=True,
    )


def _build_sidebar(
    ctx: AppContext,
    router: Router,
    current_route: str,
    on_navigate: Callable[[str], None],
    on_logout: Callable[[], None],
) -> ft.Control:
    encabezado: list[ft.Control] = []
    if ctx.show_logo_in_app and ctx.logo_path is not None:
        encabezado.append(ft.Image(src=str(ctx.logo_path), width=40, height=40))
    encabezado.append(
        ft.Text(
            ctx.business_name,
            color=theme.SIDEBAR_TEXT,
            size=16,
            weight=ft.FontWeight.BOLD,
        )
    )

    secciones: list[ft.Control] = []
    pantallas = router.visible_screens()
    pantallas_normales = [s for s in pantallas if not s.advanced]
    pantallas_avanzadas = [s for s in pantallas if s.advanced]

    for grupo, items in groupby(pantallas_normales, key=lambda s: s.group):
        items = list(items)
        secciones.append(
            ft.Text(
                grupo.upper(),
                color=theme.SIDEBAR_MUTED,
                size=11,
                weight=ft.FontWeight.BOLD,
            )
        )
        for screen in items:
            secciones.append(
                _menu_item(
                    ctx,
                    screen.route,
                    screen.label,
                    screen.icon,
                    screen.route == current_route,
                    on_navigate,
                )
            )

    if pantallas_avanzadas:
        avanzada_activa = any(s.route == current_route for s in pantallas_avanzadas)
        secciones.append(
            ft.ExpansionTile(
                title=ft.Text(
                    "CONFIGURACIÓN AVANZADA",
                    color=theme.SIDEBAR_MUTED,
                    size=11,
                    weight=ft.FontWeight.BOLD,
                ),
                expanded=avanzada_activa,
                controls=[
                    _menu_item(
                        ctx,
                        screen.route,
                        screen.label,
                        screen.icon,
                        screen.route == current_route,
                        on_navigate,
                    )
                    for screen in pantallas_avanzadas
                ],
            )
        )

    pie: list[ft.Control] = [ft.Divider(color=theme.SIDEBAR_MUTED)]
    if ctx.actor is not None:
        pie.append(ft.Text(ctx.actor.username, color=theme.SIDEBAR_TEXT))
    pie.append(
        ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.LOGOUT, color=theme.SIDEBAR_TEXT, size=16),
                    ft.Text("Cerrar sesión", color=theme.SIDEBAR_TEXT),
                ],
                spacing=theme.SPACING["sm"],
            ),
            on_click=lambda _: on_logout(),
        )
    )

    return ft.Container(
        width=SIDEBAR_WIDTH,
        bgcolor=theme.SIDEBAR,
        padding=ft.Padding.all(theme.SPACING["md"]),
        content=ft.Column(
            controls=[
                ft.Column(controls=encabezado, spacing=theme.SPACING["sm"]),
                ft.Divider(color=theme.SIDEBAR_MUTED),
                ft.Column(
                    controls=secciones,
                    spacing=theme.SPACING["xs"],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                ft.Column(controls=pie, spacing=theme.SPACING["sm"]),
            ],
            spacing=theme.SPACING["md"],
            expand=True,
        ),
    )


def build_shell(
    ctx: AppContext,
    router: Router,
    current_route: str,
    on_navigate: Callable[[str], None],
    on_logout: Callable[[], None],
) -> ft.Control:
    """Construye la fila raíz: barra lateral + contenido de la ruta actual.

    El contenido va envuelto en una `Column` con scroll propio: la barra lateral
    permanece fija y cualquier pantalla más alta que la ventana queda accesible
    desplazándose, en vez de recortarse fuera de la vista.
    """
    contenido = ft.Container(
        content=ft.Column(
            controls=[router.build(current_route)],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        bgcolor=theme.CONTENT_BG,
        padding=ft.Padding.all(theme.SPACING["lg"]),
        expand=True,
    )

    return ft.Row(
        controls=[_build_sidebar(ctx, router, current_route, on_navigate, on_logout), contenido],
        spacing=0,
        expand=True,
    )
