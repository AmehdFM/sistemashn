"""Motor genérico de generación de documentos PDF (plan fase 5, T5.4).

Promueve a módulo real la lógica validada en la sonda `pdf_probe.py` (Fase 0, T0.5b): esa sonda
se deja intacta como referencia histórica de la investigación original (no se borra ni se
modifica), pero el motor de producción vive aquí, generalizado para cualquier tipo de documento
(cotización, compra, venta, factura fiscal, recibo de abono) en lugar de un solo "comprobante
interno".

`core` no puede importar `comercial`/`repuestos`/`app` (spec §2): este módulo solo depende de
fpdf2 y de la biblioteca estándar. Los datos de negocio (montos, cantidades) llegan ya formateados
como texto en `DocumentData`: este módulo no aplica reglas de formato de negocio, solo diagrama.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fpdf import FPDF

Paper = Literal["80mm", "letter"]

PAPER_80MM: Paper = "80mm"
PAPER_LETTER: Paper = "letter"

# En Windows real se usa Arial (TTF con Unicode completo). En este repo el entorno de pruebas
# puede correr en cualquier SO (Linux/CI): si la fuente de Windows no existe, se cae a la fuente
# core `helvetica` de fpdf2 con codificación cp1252, que ya cubre ñ, tildes, ¿¡ y la raya "—"
# usadas en los documentos en español. Esto es solo un respaldo para que las pruebas corran en
# cualquier sistema operativo; en producción (Windows) siempre se preferirá Arial.
_ARIAL_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
_ARIAL_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

_80MM_WIDTH = 80.0
_80MM_MARGIN = 4.0
_80MM_MIN_HEIGHT = 100.0
_80MM_MEASURE_HEIGHT = 2000.0  # página "infinita" usada solo para medir el contenido

_LETTER_MARGIN = 15.0


@dataclass(frozen=True)
class DocumentData:
    """Contenido ya resuelto (snapshot) de un documento imprimible.

    No incluye lógica de formato de negocio: `lines` y `totals` traen los textos/montos ya
    formateados por quien arma el documento (p. ej. `DocumentService`), para que este módulo se
    mantenga genérico y sin conocer reglas de dominio.
    """

    title: str
    business_name: str
    business_address: str
    logo_path: str | None
    lines: list[tuple[str, str, str]]  # (descripción, cantidad, monto)
    totals: list[tuple[str, str]]  # (etiqueta, monto formateado)
    footer: str


def _setup_fonts(pdf: FPDF) -> str:
    """Registra Arial TTF del sistema si existe (Unicode completo).

    Si no está disponible (p. ej. en Linux/CI), cae a la fuente core `helvetica` con codificación
    cp1252, suficiente para español (ñ, tildes, ¿¡, raya "—").
    """
    if _ARIAL_REGULAR.exists() and _ARIAL_BOLD.exists():
        pdf.add_font("Arial", "", str(_ARIAL_REGULAR))
        pdf.add_font("Arial", "B", str(_ARIAL_BOLD))
        return "Arial"
    pdf.core_fonts_encoding = "cp1252"
    return "helvetica"


def _draw_document(
    pdf: FPDF, font_family: str, data: DocumentData, *, content_width: float
) -> None:
    """Dibuja el contenido de `data` en la página ya creada de `pdf`."""
    if data.logo_path is not None and Path(data.logo_path).exists():
        pdf.image(data.logo_path, w=min(30.0, content_width))
        pdf.ln(2)

    pdf.set_font(font_family, "B", 14)
    pdf.multi_cell(content_width, 6, data.business_name, align="C", new_x="LMARGIN", new_y="NEXT")
    if data.business_address:
        pdf.set_font(font_family, "", 8)
        pdf.multi_cell(
            content_width, 5, data.business_address, align="C", new_x="LMARGIN", new_y="NEXT"
        )
    pdf.ln(1)

    pdf.set_font(font_family, "B", 9)
    pdf.multi_cell(content_width, 5, data.title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    for descripcion, cantidad, monto in data.lines:
        pdf.set_font(font_family, "", 8)
        pdf.multi_cell(content_width, 5, descripcion, align="L", new_x="LMARGIN", new_y="NEXT")
        detalle = f"Cant: {cantidad}    Monto: {monto}"
        pdf.cell(content_width, 5, detalle, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    for etiqueta, monto in data.totals:
        pdf.set_font(font_family, "B", 10)
        pdf.cell(content_width, 6, f"{etiqueta}: {monto}", align="R", new_x="LMARGIN", new_y="NEXT")

    if data.footer:
        pdf.ln(4)
        pdf.set_font(font_family, "", 8)
        pdf.multi_cell(content_width, 5, data.footer, align="C", new_x="LMARGIN", new_y="NEXT")


def _build_80mm(data: DocumentData) -> FPDF:
    content_width = _80MM_WIDTH - 2 * _80MM_MARGIN

    # Primera pasada sobre una página "infinita" solo para medir cuánta altura ocupa el
    # contenido real (mismo ancho, misma fuente, mismo envolvido).
    medidor = FPDF(unit="mm", format=(_80MM_WIDTH, _80MM_MEASURE_HEIGHT))
    medidor.set_margins(_80MM_MARGIN, _80MM_MARGIN, _80MM_MARGIN)
    medidor.set_auto_page_break(False)
    fuente = _setup_fonts(medidor)
    medidor.add_page()
    _draw_document(medidor, fuente, data, content_width=content_width)
    altura_contenido = medidor.get_y() + _80MM_MARGIN
    altura_pagina = max(_80MM_MIN_HEIGHT, altura_contenido)

    pdf = FPDF(unit="mm", format=(_80MM_WIDTH, altura_pagina))
    pdf.set_margins(_80MM_MARGIN, _80MM_MARGIN, _80MM_MARGIN)
    pdf.set_auto_page_break(False)
    fuente = _setup_fonts(pdf)
    pdf.add_page()
    _draw_document(pdf, fuente, data, content_width=content_width)
    return pdf


def _build_letter(data: DocumentData) -> FPDF:
    pdf = FPDF(unit="mm", format=PAPER_LETTER)
    pdf.set_margins(_LETTER_MARGIN, _LETTER_MARGIN, _LETTER_MARGIN)
    pdf.set_auto_page_break(True, margin=_LETTER_MARGIN)
    fuente = _setup_fonts(pdf)
    content_width = pdf.w - 2 * _LETTER_MARGIN
    pdf.add_page()
    _draw_document(pdf, fuente, data, content_width=content_width)
    return pdf


def render(data: DocumentData, *, paper: Paper) -> bytes:
    """Genera el PDF de `data` en memoria y devuelve sus bytes.

    `fpdf2` 2.8.x devuelve un `bytearray` al pasar `dest="S"` a `FPDF.output`; se convierte
    explícitamente a `bytes` para que el contrato de esta función sea estable.
    """
    if paper == PAPER_80MM:
        pdf = _build_80mm(data)
    elif paper == PAPER_LETTER:
        pdf = _build_letter(data)
    else:
        raise ValueError(f"papel no soportado: {paper!r}")
    return bytes(pdf.output())
