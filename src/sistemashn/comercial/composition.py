"""Registro de los servicios de Comercial en el contexto de la aplicación."""

from sistemashn.comercial.catalogo.excel import ExcelImportService
from sistemashn.comercial.catalogo.kits import KitService
from sistemashn.comercial.catalogo.search import ProductSearchProvider
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.compras.service import PurchaseService
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.credito.service import AccountService
from sistemashn.comercial.inventario.ledger import InventoryLedger
from sistemashn.comercial.inventario.service import InventoryService
from sistemashn.comercial.ui.extensions import PRODUCT_FORM_EXTENSIONS_KEY
from sistemashn.core.ui.app_context import AppContext


def register_services(
    ctx: AppContext,
    *,
    search_providers: list[ProductSearchProvider] | None = None,
    excel_extensions: list | None = None,
) -> None:
    """Servicios en `ctx.services`: catalog, ledger, inventory, kits, excel, parties, accounts,
    purchases."""
    factory, authorizer, clock = ctx.session_factory, ctx.authorizer, ctx.clock
    ledger = InventoryLedger(clock)
    catalog = CatalogService(factory, authorizer, clock, search_providers=search_providers)
    accounts = AccountService(factory, authorizer, clock)
    ctx.services["catalog"] = catalog
    ctx.services["ledger"] = ledger
    ctx.services["inventory"] = InventoryService(factory, authorizer, clock, ledger)
    ctx.services["kits"] = KitService(factory, authorizer, clock)
    ctx.services["excel"] = ExcelImportService(
        factory, authorizer, clock, catalog_service=catalog, extensions=excel_extensions or []
    )
    ctx.services["parties"] = PartyService(factory, authorizer, clock)
    ctx.services["accounts"] = accounts
    ctx.services["purchases"] = PurchaseService(factory, authorizer, clock, ledger, accounts)
    ctx.services.setdefault(PRODUCT_FORM_EXTENSIONS_KEY, [])
