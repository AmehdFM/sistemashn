"""Registro de los servicios de Repuestos en el contexto de la aplicación."""

from sistemashn.comercial.ui.extensions import PRODUCT_FORM_EXTENSIONS_KEY
from sistemashn.core.ui.app_context import AppContext
from sistemashn.repuestos.excel import RepuestosExcelExtension
from sistemashn.repuestos.partes.search import RepuestosSearchProvider
from sistemashn.repuestos.partes.service import PartService
from sistemashn.repuestos.ui.part_extension import PartFormExtension
from sistemashn.repuestos.vehiculos.service import VehicleService


def search_providers() -> list:
    return [RepuestosSearchProvider()]


def excel_extensions() -> list:
    return [RepuestosExcelExtension()]


def register_services(ctx: AppContext) -> None:
    """Nombres en `ctx.services`: parts, vehicles."""
    factory, authorizer, clock = ctx.session_factory, ctx.authorizer, ctx.clock
    ctx.services["parts"] = PartService(factory, authorizer, clock)
    ctx.services["vehicles"] = VehicleService(factory, authorizer, clock)
    ctx.services.setdefault(PRODUCT_FORM_EXTENSIONS_KEY, []).append(PartFormExtension())
