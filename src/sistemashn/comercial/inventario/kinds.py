"""Tipos de movimiento del libro de inventario (plan T2.2)."""

from enum import StrEnum


class MovementKind(StrEnum):
    PURCHASE_IN = "purchase_in"
    SALE_OUT = "sale_out"
    RESERVE = "reserve"
    RELEASE = "release"
    CUSTOMER_RETURN_SELLABLE = "customer_return_sellable"
    CUSTOMER_RETURN_UNSELLABLE = "customer_return_unsellable"
    SUPPLIER_RETURN_OUT = "supplier_return_out"
    UNSELLABLE_RESOLVED = "unsellable_resolved"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    VOID_REVERSAL = "void_reversal"
