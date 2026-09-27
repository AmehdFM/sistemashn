"""Sonda de generación de PDF y flujo de impresión (Fase 0, T0.5b).

Este módulo NO es el motor de facturación definitivo: solo valida que fpdf2
puede producir comprobantes internos en 80mm y carta, con texto en español
completo (ñ, tildes, ¿¡), y que Windows puede imprimirlos/abrirlos sin
bloquear la aplicación cuando no hay impresora configurada.

`core` no puede importar `comercial`/`repuestos`/`app` (spec §2): este
módulo solo depende de fpdf2 y de la biblioteca estándar.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fpdf import FPDF

PAPER_LETTER = "letter"
PAPER_80MM = "80mm"

_ARIAL_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
_ARIAL_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

_80MM_WIDTH = 80.0
_80MM_MARGIN = 4.0
_80MM_MIN_HEIGHT = 100.0
_80MM_MEASURE_HEIGHT = 2000.0  # página "infinita" usada solo para medir el contenido

_LETTER_MARGIN = 15.0

_TITLE = "COMPROBANTE INTERNO — NO FISCAL"
_FOOTER = "¡Gracias por su compra! Año, niño, acción, ¿dudas?"

LineaComprobante = tuple[str, Decimal, Decimal]


@dataclass(frozen=True)
class PrintOutcome:
    """Resultado de intentar imprimir o abrir un PDF."""

    sent: bool
    detail: str


def format_lempiras(value: Decimal) -> str:
    """Formatea un monto como moneda hondureña: `L 1,234.56` (negativos `-L 5.00`)."""
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negative = quantized < 0
    magnitude = -quantized if negative else quantized
    formatted = f"{magnitude:,.2f}"
    return f"-L {formatted}" if negative else f"L {formatted}"


def _format_cantidad(value: Decimal) -> str:
    """Formatea una cantidad sin ceros de relleno (3 -> '3', 2.500 -> '2.5')."""
    quantized = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _setup_fonts(pdf: FPDF) -> str:
    """Registra Arial TTF del sistema si existe (Unicode completo).

    Si no está disponible, cae a la fuente core `helvetica` (latin-1, suficiente
    para español: ñ, tildes, ¿¡ están en Latin-1).
    """
    if _ARIAL_REGULAR.exists() and _ARIAL_BOLD.exists():
        pdf.add_font("Arial", "", str(_ARIAL_REGULAR))
        pdf.add_font("Arial", "B", str(_ARIAL_BOLD))
        return "Arial"
    # cp1252 cubre ñ, tildes, ¿¡ y la raya "—" que latin-1 (default) no soporta.
    pdf.core_fonts_encoding = "cp1252"
    return "helvetica"


def _draw_receipt(
    pdf: FPDF,
    font_family: str,
    *,
    business_name: str,
    lines: list[LineaComprobante],
    logo: Path | None,
    content_width: float,
) -> None:
    """Dibuja el contenido del comprobante en la página ya creada de `pdf`."""
    if logo is not None:
        pdf.image(str(logo), w=min(30.0, content_width))
        pdf.ln(2)

    pdf.set_font(font_family, "B", 14)
    pdf.multi_cell(content_width, 6, business_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font(font_family, "B", 9)
    pdf.multi_cell(content_width, 5, _TITLE, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font(font_family, "", 8)
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(content_width, 5, f"Fecha: {fecha}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    total = Decimal("0")
    for descripcion, cantidad, importe in lines:
        pdf.set_font(font_family, "", 8)
        pdf.multi_cell(content_width, 5, descripcion, align="L", new_x="LMARGIN", new_y="NEXT")
        detalle = f"Cant: {_format_cantidad(cantidad)}    Total: {format_lempiras(importe)}"
        pdf.cell(content_width, 5, detalle, align="R", new_x="LMARGIN", new_y="NEXT")
        total += importe

    pdf.ln(2)
    pdf.set_font(font_family, "B", 10)
    pdf.cell(
        content_width,
        6,
        f"TOTAL: {format_lempiras(total)}",
        align="R",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(4)
    pdf.set_font(font_family, "", 8)
    pdf.multi_cell(content_width, 5, _FOOTER, align="C", new_x="LMARGIN", new_y="NEXT")


def _build_80mm(*, business_name: str, lines: list[LineaComprobante], logo: Path | None) -> FPDF:
    content_width = _80MM_WIDTH - 2 * _80MM_MARGIN

    # Primera pasada sobre una página "infinita" solo para medir cuánta altura
    # ocupa el contenido real (mismo ancho, misma fuente, mismo envolvido).
    medidor = FPDF(unit="mm", format=(_80MM_WIDTH, _80MM_MEASURE_HEIGHT))
    medidor.set_margins(_80MM_MARGIN, _80MM_MARGIN, _80MM_MARGIN)
    medidor.set_auto_page_break(False)
    fuente = _setup_fonts(medidor)
    medidor.add_page()
    _draw_receipt(
        medidor,
        fuente,
        business_name=business_name,
        lines=lines,
        logo=logo,
        content_width=content_width,
    )
    altura_contenido = medidor.get_y() + _80MM_MARGIN
    altura_pagina = max(_80MM_MIN_HEIGHT, altura_contenido)

    pdf = FPDF(unit="mm", format=(_80MM_WIDTH, altura_pagina))
    pdf.set_margins(_80MM_MARGIN, _80MM_MARGIN, _80MM_MARGIN)
    pdf.set_auto_page_break(False)
    fuente = _setup_fonts(pdf)
    pdf.add_page()
    _draw_receipt(
        pdf,
        fuente,
        business_name=business_name,
        lines=lines,
        logo=logo,
        content_width=content_width,
    )
    return pdf


def _build_letter(*, business_name: str, lines: list[LineaComprobante], logo: Path | None) -> FPDF:
    pdf = FPDF(unit="mm", format=PAPER_LETTER)
    pdf.set_margins(_LETTER_MARGIN, _LETTER_MARGIN, _LETTER_MARGIN)
    pdf.set_auto_page_break(True, margin=_LETTER_MARGIN)
    fuente = _setup_fonts(pdf)
    content_width = pdf.w - 2 * _LETTER_MARGIN
    pdf.add_page()
    _draw_receipt(
        pdf,
        fuente,
        business_name=business_name,
        lines=lines,
        logo=logo,
        content_width=content_width,
    )
    return pdf


def build_probe_pdf(
    paper: str,
    *,
    business_name: str,
    lines: list[LineaComprobante],
    logo: Path | None = None,
) -> FPDF:
    """Construye (sin guardar) el objeto FPDF del comprobante de ensayo.

    Se expone por separado de `render_probe_receipt` para poder inspeccionar
    `pages_count` y las dimensiones de página en pruebas.
    """
    if paper == PAPER_80MM:
        return _build_80mm(business_name=business_name, lines=lines, logo=logo)
    if paper == PAPER_LETTER:
        return _build_letter(business_name=business_name, lines=lines, logo=logo)
    raise ValueError(f"papel no soportado: {paper!r}")


def render_probe_receipt(
    path: Path,
    paper: str,
    *,
    business_name: str,
    lines: list[LineaComprobante],
    logo: Path | None = None,
) -> Path:
    """Genera el PDF de ensayo en `path` y devuelve la ruta."""
    pdf = build_probe_pdf(paper, business_name=business_name, lines=lines, logo=logo)
    path = Path(path)
    pdf.output(str(path))
    return path


def print_pdf(path: Path) -> PrintOutcome:
    """Intenta imprimir `path` en la impresora predeterminada de Windows.

    Nunca lanza: si no hay impresora configurada o no existe asociación de
    impresión para PDF, devuelve `sent=False` con el detalle del error.
    """
    if os.name != "nt":
        return PrintOutcome(sent=False, detail="impresión directa solo soportada en Windows")
    try:
        os.startfile(str(path), "print")  # type: ignore[attr-defined]
    except OSError as exc:
        return PrintOutcome(sent=False, detail=str(exc))
    return PrintOutcome(sent=True, detail="enviado a la impresora predeterminada")


def open_pdf(path: Path) -> PrintOutcome:
    """Abre `path` con la aplicación asociada de Windows (visor de PDF).

    Igual que `print_pdf`, nunca lanza ante falta de asociación.
    """
    if os.name != "nt":
        return PrintOutcome(sent=False, detail="apertura directa solo soportada en Windows")
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except OSError as exc:
        return PrintOutcome(sent=False, detail=str(exc))
    return PrintOutcome(sent=True, detail="abierto con la aplicación asociada")
