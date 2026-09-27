"""Armado de documentos imprimibles a partir de vistas ya materializadas (plan T5.4).

`DocumentService` es una utilidad de formateo puro: recibe vistas de solo lectura ya obtenidas
(y por tanto ya autorizadas) por el llamador, y no abre sesión de base de datos ni recibe
`Actor`/`AppContext`. Nunca vuelve a consultar el catálogo en vivo: todos los textos y montos
salen de la vista recibida, así que un documento ya generado no cambia si el producto o el
negocio cambian después.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

from sistemashn.comercial.compras.schemas import PurchaseView
from sistemashn.comercial.cotizaciones.schemas import QuoteView
from sistemashn.comercial.credito.schemas import AccountPaymentView
from sistemashn.comercial.fiscal.schemas import FiscalInvoiceView
from sistemashn.comercial.ventas.schemas import SaleView
from sistemashn.core.documents.pdf_probe import format_lempiras
from sistemashn.core.documents.renderer import DocumentData, Paper, render

_TITULO_COMPROBANTE_INTERNO = "COMPROBANTE INTERNO — NO FISCAL"


def _cantidad(value: Decimal) -> str:
    """Formatea una cantidad sin ceros de relleno (3 -> '3', 2.500 -> '2.5')."""
    text = format(value.normalize(), "f")
    return text


class DocumentService:
    """Construye `DocumentData` a partir de vistas de comercial y delega el render a `core`."""

    def for_quote(
        self,
        quote: QuoteView,
        *,
        business_name: str,
        business_address: str,
        logo_path: str | None = None,
    ) -> DocumentData:
        lines = [
            (line.description_snapshot, _cantidad(line.qty), format_lempiras(line.line_total))
            for line in quote.lines
        ]
        totals = [
            ("Subtotal", format_lempiras(quote.subtotal)),
            ("Impuesto", format_lempiras(quote.tax_total)),
            ("Total", format_lempiras(quote.total)),
        ]
        return DocumentData(
            title=f"Cotización {quote.number}",
            business_name=business_name,
            business_address=business_address,
            logo_path=logo_path,
            lines=lines,
            totals=totals,
            footer=f"Válida hasta: {quote.valid_until.isoformat()}",
        )

    def for_purchase(
        self,
        purchase: PurchaseView,
        *,
        business_name: str,
        business_address: str,
        logo_path: str | None = None,
    ) -> DocumentData:
        lines = [
            (line.description_snapshot, _cantidad(line.qty), format_lempiras(line.line_total))
            for line in purchase.lines
        ]
        totals = [
            ("Subtotal", format_lempiras(purchase.subtotal)),
            ("Impuesto", format_lempiras(purchase.tax_total)),
            ("Total", format_lempiras(purchase.total)),
        ]
        footer = purchase.supplier_invoice_ref or ""
        return DocumentData(
            title=f"Comprobante de compra {purchase.number}",
            business_name=business_name,
            business_address=business_address,
            logo_path=logo_path,
            lines=lines,
            totals=totals,
            footer=footer,
        )

    def for_sale(
        self,
        sale: SaleView,
        *,
        business_name: str,
        business_address: str,
        logo_path: str | None = None,
    ) -> DocumentData:
        lines = [
            (line.description_snapshot, _cantidad(line.qty), format_lempiras(line.line_total))
            for line in sale.lines
        ]
        totals = [
            ("Subtotal", format_lempiras(sale.subtotal)),
            ("Impuesto", format_lempiras(sale.tax_total)),
            ("Total", format_lempiras(sale.total)),
            ("Pagado", format_lempiras(sale.paid_amount)),
            ("Cambio", format_lempiras(sale.change_amount)),
        ]
        return DocumentData(
            title=f"{_TITULO_COMPROBANTE_INTERNO} — {sale.number}",
            business_name=business_name,
            business_address=business_address,
            logo_path=logo_path,
            lines=lines,
            totals=totals,
            footer="¡Gracias por su compra!",
        )

    def for_fiscal_invoice(
        self,
        invoice: FiscalInvoiceView,
        sale: SaleView,
        *,
        business_name: str,
        business_address: str,
        logo_path: str | None = None,
    ) -> DocumentData:
        # `FiscalInvoiceView` no expone un desglose de líneas propio (el `snapshot_json` del
        # modelo es texto crudo sin estructura definida por este spec): las líneas de la factura
        # fiscal son las mismas de la venta asociada, que ya es un snapshot inmutable de lo
        # vendido, así que reutilizarlas no reintroduce datos "en vivo".
        lines = [
            (line.description_snapshot, _cantidad(line.qty), format_lempiras(line.line_total))
            for line in sale.lines
        ]
        totals = [
            ("Subtotal", format_lempiras(sale.subtotal)),
            ("Impuesto", format_lempiras(sale.tax_total)),
            ("Total", format_lempiras(sale.total)),
        ]
        return DocumentData(
            title=f"Factura fiscal {invoice.fiscal_number}",
            business_name=business_name,
            business_address=business_address,
            logo_path=logo_path,
            lines=lines,
            totals=totals,
            footer=f"CAI válido - emitida {invoice.issued_at.isoformat()}",
        )

    def for_receipt(
        self,
        payment: AccountPaymentView,
        *,
        account_number_or_ref: str,
        party_name: str,
        business_name: str,
        business_address: str,
        logo_path: str | None = None,
    ) -> DocumentData:
        lines = [
            (
                f"Abono a cuenta {account_number_or_ref} — {party_name}",
                "1",
                format_lempiras(payment.amount),
            )
        ]
        totals = [("Total abonado", format_lempiras(payment.amount))]
        referencia = f" (ref: {payment.reference})" if payment.reference else ""
        return DocumentData(
            title=f"Recibo de abono — {account_number_or_ref}",
            business_name=business_name,
            business_address=business_address,
            logo_path=logo_path,
            lines=lines,
            totals=totals,
            footer=f"Método: {payment.method}{referencia}",
        )

    def save_pdf(self, data: DocumentData, path: str | Path, *, paper: Paper) -> None:
        """Genera el PDF de `data` y lo escribe en `path`."""
        contenido = render(data, paper=paper)
        Path(path).write_bytes(contenido)

    def print_pdf(self, path: str | Path) -> bool:
        """Envía `path` a la impresora predeterminada de Windows.

        En cualquier otro sistema operativo (o si no hay impresora/asociación configurada en
        Windows) degrada sin error: devuelve `False` en lugar de lanzar una excepción.
        """
        if os.name != "nt":
            return False
        try:
            os.startfile(str(path), "print")  # type: ignore[attr-defined]
        except OSError:
            return False
        return True
