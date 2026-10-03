"""Esquemas de solo lectura de los reportes (plan T5.5).

`SalesProfitRow` reporta a nivel de venta (una fila por `com_sale`), no por línea: es el nivel
de detalle más simple que responde la pregunta de negocio ("¿cuánto vendí y cuánto gané en este
rango?") sin duplicar información entre la línea de kit-encabezado y sus componentes. Quien
necesite el detalle por producto ya cuenta con `SaleService.get`/`.list` para profundizar en una
venta puntual.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class SalesProfitRow:
    """Una venta confirmada dentro del rango del reporte."""

    sale_id: int
    number: str
    sold_at: datetime
    customer_id: int | None
    total: Decimal
    cost: Decimal | None
    profit: Decimal | None


@dataclass(frozen=True)
class SalesProfitReport:
    rows: tuple[SalesProfitRow, ...]
    total_sales: Decimal
    total_cost: Decimal | None
    total_profit: Decimal | None
    since: datetime
    until: datetime
    incomplete_cost_sales: int = 0
    unlinked_returns: int = 0


@dataclass(frozen=True)
class LowStockRow:
    """Envuelve `InventoryService.LowStockItem`: mismo esquema, nombre propio del paquete."""

    product_id: int
    code: str
    name: str
    on_hand: Decimal
    reserved: Decimal
    available: Decimal
    min_stock: Decimal


@dataclass(frozen=True)
class AccountBalanceRow:
    id: int
    party_name: str
    kind: str
    balance: Decimal
    due_date: date
    status: str


@dataclass(frozen=True)
class CashClosureRow:
    id: int
    opened_at: datetime
    closed_at: datetime
    opening_amount: Decimal
    expected_cash: Decimal
    counted_cash: Decimal
    difference: Decimal
