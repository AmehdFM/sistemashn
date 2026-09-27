"""Constructores de las pantallas de Comercial, indexados por ruta de `COMERCIAL_MODULE`."""

from sistemashn.comercial.ui.catalog_view import build_catalog_view
from sistemashn.comercial.ui.compras_view import build_new_purchase_view, build_purchases_view
from sistemashn.comercial.ui.contrapartes_view import build_parties_view
from sistemashn.comercial.ui.cxp_view import build_cxp_view
from sistemashn.comercial.ui.import_view import build_import_view
from sistemashn.comercial.ui.inventory_view import build_inventory_view
from sistemashn.comercial.ui.low_stock_view import build_low_stock_view
from sistemashn.core.ui.router import ScreenBuilder

COMERCIAL_SCREEN_BUILDERS: dict[str, ScreenBuilder] = {
    "/catalogo": build_catalog_view,
    "/catalogo/importar": build_import_view,
    "/inventario": build_inventory_view,
    "/inventario/stock-bajo": build_low_stock_view,
    "/contrapartes": build_parties_view,
    "/compras": build_purchases_view,
    "/compras/nueva": build_new_purchase_view,
    "/cxp": build_cxp_view,
}
