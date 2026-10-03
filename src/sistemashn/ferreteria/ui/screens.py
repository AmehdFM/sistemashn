"""Constructores de pantallas de Ferretería."""

from sistemashn.core.ui.router import ScreenBuilder
from sistemashn.ferreteria.ui.presentations_view import build_presentations_view
from sistemashn.ferreteria.ui.summary_view import build_summary_view

FERRETERIA_SCREEN_BUILDERS: dict[str, ScreenBuilder] = {
    "/ferreteria/resumen": build_summary_view,
    "/ferreteria/presentaciones": build_presentations_view,
}
