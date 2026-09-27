"""Pruebas del motor genérico de render PDF (plan T5.4)."""

from __future__ import annotations

from pathlib import Path

from sistemashn.core.documents.renderer import DocumentData, render


def _datos(**overrides: object) -> DocumentData:
    base = dict(
        title="Cotización COT-0001",
        business_name="Repuestos Año Nuevo, S. de R.L.",
        business_address="Barrio El Centro, Tegucigalpa",
        logo_path=None,
        lines=[("Filtro de aceite ñoño ¿1/2?", "2", "L 200.00")],
        totals=[("Total", "L 200.00")],
        footer="¡Gracias por su compra! Año, niño, acción, ¿dudas?",
    )
    base.update(overrides)
    return DocumentData(**base)  # type: ignore[arg-type]


def test_render_80mm_produce_pdf_valido() -> None:
    contenido = render(_datos(), paper="80mm")
    assert contenido.startswith(b"%PDF")


def test_render_letter_produce_pdf_valido() -> None:
    contenido = render(_datos(), paper="letter")
    assert contenido.startswith(b"%PDF")


def test_render_acepta_logo_inexistente_sin_fallar(tmp_path: Path) -> None:
    contenido = render(_datos(logo_path=str(tmp_path / "no_existe.png")), paper="80mm")
    assert contenido.startswith(b"%PDF")


def test_render_paper_invalido_lanza_value_error() -> None:
    try:
        render(_datos(), paper="a4")  # type: ignore[arg-type]
    except ValueError:
        return
    raise AssertionError("se esperaba ValueError para papel no soportado")
