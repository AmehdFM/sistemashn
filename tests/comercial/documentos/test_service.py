"""Pruebas de `DocumentService` (plan T5.4)."""

from __future__ import annotations

import inspect
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sistemashn.comercial.compras.schemas import PurchaseLineView, PurchaseView
from sistemashn.comercial.cotizaciones.schemas import QuoteLineView, QuoteView
from sistemashn.comercial.credito.schemas import AccountPaymentView
from sistemashn.comercial.documentos.service import DocumentService
from sistemashn.comercial.fiscal.schemas import FiscalInvoiceView
from sistemashn.comercial.ventas.schemas import SaleLineView, SalePaymentView, SaleView
from sistemashn.core.documents.renderer import render

_NEGOCIO = {"business_name": "Repuestos Año Nuevo", "business_address": "Tegucigalpa, ¿centro?"}


def _quote() -> QuoteView:
    linea = QuoteLineView(
        line_no=1,
        product_id=1,
        description_snapshot="Filtro de aceite ñ",
        qty=Decimal("2"),
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("0.15"),
        line_subtotal=Decimal("200.00"),
        line_tax=Decimal("30.00"),
        line_total=Decimal("230.00"),
    )
    return QuoteView(
        id=1,
        uuid="uuid-1",
        number="COT-0001",
        customer_id=None,
        status="vigente",
        valid_until=date(2026, 12, 31),
        has_reservation=False,
        subtotal=Decimal("200.00"),
        tax_total=Decimal("30.00"),
        total=Decimal("230.00"),
        notes=None,
        created_at=datetime(2026, 1, 1),
        lines=(linea,),
    )


def _purchase() -> PurchaseView:
    linea = PurchaseLineView(
        line_no=1,
        product_id=1,
        description_snapshot="Batería 12V",
        qty=Decimal("1"),
        unit_cost=Decimal("500.00"),
        tax_rate=Decimal("0.15"),
        line_subtotal=Decimal("500.00"),
        line_tax=Decimal("75.00"),
        line_total=Decimal("575.00"),
    )
    return PurchaseView(
        id=1,
        uuid="uuid-2",
        number="COM-0001",
        supplier_id=1,
        supplier_invoice_ref="F-001",
        purchased_at=datetime(2026, 1, 1),
        subtotal=Decimal("500.00"),
        tax_total=Decimal("75.00"),
        total=Decimal("575.00"),
        paid_initial=Decimal("575.00"),
        credit_amount=Decimal("0"),
        status="confirmada",
        notes=None,
        created_at=datetime(2026, 1, 1),
        lines=(linea,),
        payments=(),
    )


def _sale() -> SaleView:
    linea = SaleLineView(
        line_no=1,
        product_id=1,
        description_snapshot="Pastillas de freno ¿delanteras?",
        qty=Decimal("1"),
        unit_price=Decimal("300.00"),
        tax_rate=Decimal("0.15"),
        line_subtotal=Decimal("300.00"),
        line_tax=Decimal("45.00"),
        line_total=Decimal("345.00"),
        unit_cost_snapshot=Decimal("200.00"),
        kit_component_of=None,
    )
    pago = SalePaymentView(method="efectivo", amount=Decimal("345.00"), reference=None)
    return SaleView(
        id=1,
        uuid="uuid-3",
        number="VTA-0001",
        quote_id=None,
        customer_id=None,
        sold_at=datetime(2026, 1, 1),
        subtotal=Decimal("300.00"),
        tax_total=Decimal("45.00"),
        total=Decimal("345.00"),
        paid_amount=Decimal("345.00"),
        change_amount=Decimal("0"),
        credit_amount=Decimal("0"),
        status="confirmada",
        cash_session_id=None,
        notes=None,
        created_at=datetime(2026, 1, 1),
        lines=(linea,),
        payments=(pago,),
    )


def _account_payment() -> AccountPaymentView:
    return AccountPaymentView(
        id=1,
        paid_at=datetime(2026, 1, 1),
        method="efectivo",
        amount=Decimal("100.00"),
        reference="REF-1",
        user_id=1,
    )


def test_for_quote_produce_documento_renderizable() -> None:
    servicio = DocumentService()
    data = servicio.for_quote(_quote(), **_NEGOCIO)
    assert data.lines and data.totals
    assert render(data, paper="80mm").startswith(b"%PDF")
    assert render(data, paper="letter").startswith(b"%PDF")


def test_for_purchase_produce_documento_renderizable() -> None:
    servicio = DocumentService()
    data = servicio.for_purchase(_purchase(), **_NEGOCIO)
    assert data.lines and data.totals
    assert render(data, paper="80mm").startswith(b"%PDF")


def test_for_sale_produce_documento_renderizable() -> None:
    servicio = DocumentService()
    data = servicio.for_sale(_sale(), **_NEGOCIO)
    assert "COMPROBANTE INTERNO" in data.title
    assert render(data, paper="80mm").startswith(b"%PDF")


def test_for_fiscal_invoice_produce_documento_renderizable() -> None:
    servicio = DocumentService()
    factura = FiscalInvoiceView(
        id=1,
        sale_id=1,
        authorization_id=1,
        fiscal_number="000-001-01-00000001",
        issued_at=datetime(2026, 1, 1),
    )
    data = servicio.for_fiscal_invoice(factura, _sale(), **_NEGOCIO)
    assert data.lines and data.totals
    assert render(data, paper="letter").startswith(b"%PDF")


def test_for_receipt_produce_documento_renderizable() -> None:
    servicio = DocumentService()
    data = servicio.for_receipt(
        _account_payment(),
        account_number_or_ref="CTA-0001",
        party_name="Cliente de prueba",
        **_NEGOCIO,
    )
    assert data.lines and data.totals
    assert render(data, paper="80mm").startswith(b"%PDF")


def test_for_sale_y_for_purchase_no_reciben_sesion_ni_contexto() -> None:
    """Las firmas solo toman la vista ya materializada: nunca session/ctx/Actor."""
    for metodo in (
        DocumentService.for_sale,
        DocumentService.for_purchase,
        DocumentService.for_quote,
    ):
        parametros = set(inspect.signature(metodo).parameters)
        assert "session" not in parametros
        assert "ctx" not in parametros
        assert "actor" not in parametros


def test_save_pdf_escribe_archivo_real(tmp_path: Path) -> None:
    servicio = DocumentService()
    data = servicio.for_sale(_sale(), **_NEGOCIO)
    destino = tmp_path / "venta.pdf"
    servicio.save_pdf(data, destino, paper="80mm")
    assert destino.read_bytes().startswith(b"%PDF")


def test_print_pdf_en_linux_devuelve_false_sin_lanzar(tmp_path: Path) -> None:
    if os.name == "nt":
        return
    servicio = DocumentService()
    destino = tmp_path / "venta.pdf"
    destino.write_bytes(b"%PDF-1.4\n")
    assert servicio.print_pdf(destino) is False
