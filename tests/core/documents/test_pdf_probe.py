"""Sonda de PDF/impresión (T0.5b): fpdf2 genera comprobantes válidos."""

import os
from decimal import Decimal
from pathlib import Path

import pytest

from sistemashn.core.documents import pdf_probe
from sistemashn.core.documents.pdf_probe import (
    PAPER_80MM,
    PAPER_LETTER,
    PrintOutcome,
    build_probe_pdf,
    format_lempiras,
    print_pdf,
    render_probe_receipt,
)

SHORT_LINES: list[tuple[str, Decimal, Decimal]] = [
    ("Filtro de aceite", Decimal("2"), Decimal("350.00")),
    ("Bujía NGK", Decimal("4"), Decimal("640.00")),
]


def _long_lines(n: int) -> list[tuple[str, Decimal, Decimal]]:
    return [
        (
            f"Repuesto genérico número {i} con descripción larga que debe envolver "
            "varias líneas dentro del comprobante sin cortarse nunca, ¿verdad que sí?",
            Decimal("1"),
            Decimal("100.00"),
        )
        for i in range(n)
    ]


def test_render_probe_receipt_80mm_crea_pdf_valido(tmp_path: Path) -> None:
    destino = tmp_path / "probe-80mm.pdf"

    resultado = render_probe_receipt(
        destino, PAPER_80MM, business_name="Repuestos Ñandú", lines=SHORT_LINES
    )

    assert resultado == destino
    assert destino.exists()
    assert destino.read_bytes()[:4] == b"%PDF"


def test_render_probe_receipt_carta_crea_pdf_valido(tmp_path: Path) -> None:
    destino = tmp_path / "probe-carta.pdf"

    render_probe_receipt(destino, PAPER_LETTER, business_name="Repuestos Ñandú", lines=SHORT_LINES)

    assert destino.exists()
    assert destino.read_bytes()[:4] == b"%PDF"


def test_80mm_con_muchas_lineas_largas_es_una_sola_pagina_alta() -> None:
    pdf = build_probe_pdf(PAPER_80MM, business_name="Repuestos Ñandú", lines=_long_lines(40))

    assert pdf.pages_count == 1
    assert round(pdf.w) == 80
    assert pdf.h > 100


def test_carta_con_muchas_lineas_largas_puede_paginar() -> None:
    pdf = build_probe_pdf(PAPER_LETTER, business_name="Repuestos Ñandú", lines=_long_lines(40))

    assert pdf.pages_count >= 2


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("0"), "L 0.00"),
        (Decimal("1234.5"), "L 1,234.50"),
        (Decimal("-5"), "-L 5.00"),
        (Decimal("1000000"), "L 1,000,000.00"),
    ],
)
def test_format_lempiras(valor: Decimal, esperado: str) -> None:
    assert format_lempiras(valor) == esperado


def test_texto_con_enie_e_interrogaciones_no_lanza_con_fuente_core(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(pdf_probe, "_ARIAL_REGULAR", Path("C:/no/existe/arial.ttf"))
    monkeypatch.setattr(pdf_probe, "_ARIAL_BOLD", Path("C:/no/existe/arialbd.ttf"))

    destino = tmp_path / "core-font.pdf"
    render_probe_receipt(
        destino,
        PAPER_80MM,
        business_name="Ñoño & Cía, ¿acción?",
        lines=[("Año nuevo niño", Decimal("1"), Decimal("10.00"))],
    )

    assert destino.exists()
    assert destino.read_bytes()[:4] == b"%PDF"


def test_setup_fonts_usa_helvetica_cuando_no_hay_arial(monkeypatch: pytest.MonkeyPatch) -> None:
    from fpdf import FPDF

    monkeypatch.setattr(pdf_probe, "_ARIAL_REGULAR", Path("C:/no/existe/arial.ttf"))
    monkeypatch.setattr(pdf_probe, "_ARIAL_BOLD", Path("C:/no/existe/arialbd.ttf"))

    pdf = FPDF()
    assert pdf_probe._setup_fonts(pdf) == "helvetica"


def test_print_pdf_sin_impresora_no_lanza(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    destino = tmp_path / "a imprimir.pdf"
    destino.write_bytes(b"%PDF-1.4\n%fake")

    def _boom(path: str, operation: str | None = None) -> None:
        raise OSError("no hay impresora asociada")

    monkeypatch.setattr(os, "startfile", _boom, raising=False)

    resultado = print_pdf(destino)

    assert isinstance(resultado, PrintOutcome)
    assert resultado.sent is False
    assert resultado.detail


def test_ruta_con_espacios_y_acentos(tmp_path: Path) -> None:
    carpeta = tmp_path / "carpeta con ñ y acentós"
    carpeta.mkdir()
    destino = carpeta / "recibo áéí.pdf"

    render_probe_receipt(destino, PAPER_80MM, business_name="Prueba", lines=SHORT_LINES)

    assert destino.exists()
    assert destino.read_bytes()[:4] == b"%PDF"
