"""Servicios y extensiones de Ferretería sobre Comercial."""

from sistemashn.comercial.ui.extensions import PRODUCT_FORM_EXTENSIONS_KEY
from sistemashn.core.ui.app_context import AppContext
from sistemashn.ferreteria.catalogo.search import FerreteriaSearchProvider
from sistemashn.ferreteria.catalogo.service import FerreteriaCatalogService
from sistemashn.ferreteria.operaciones import FerreteriaLineBuilder
from sistemashn.ferreteria.ui.item_extension import ItemFormExtension


def search_providers() -> list[FerreteriaSearchProvider]:
    return [FerreteriaSearchProvider()]


def register_services(ctx: AppContext) -> None:
    fer_catalog = FerreteriaCatalogService(ctx.session_factory, ctx.authorizer, ctx.clock)
    ctx.services["fer_catalog"] = fer_catalog
    ctx.services["fer_lines"] = FerreteriaLineBuilder(fer_catalog, ctx.session_factory)
    ctx.services.setdefault(PRODUCT_FORM_EXTENSIONS_KEY, []).append(ItemFormExtension())
