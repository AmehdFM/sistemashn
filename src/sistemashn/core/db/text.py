"""Helpers de texto para consultas SQL."""

LIKE_ESCAPE = "\\"


def escape_like(text: str) -> str:
    """Escapa `%`, `_` y la barra para que el texto del usuario se busque literal en LIKE."""
    return text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
