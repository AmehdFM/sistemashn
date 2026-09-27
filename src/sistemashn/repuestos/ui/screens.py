"""Constructores de las pantallas de Repuestos, indexados por ruta de `REPUESTOS_MODULE`."""

from sistemashn.core.ui.router import ScreenBuilder
from sistemashn.repuestos.ui.compatible_view import build_compatible_view
from sistemashn.repuestos.ui.vehicles_view import build_vehicles_view

REPUESTOS_SCREEN_BUILDERS: dict[str, ScreenBuilder] = {
    "/repuestos/vehiculos": build_vehicles_view,
    "/repuestos/compatibles": build_compatible_view,
}
