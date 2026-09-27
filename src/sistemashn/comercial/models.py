"""Registra en `Base.metadata` los modelos de Comercial que no viven en un submódulo propio.

`tests/conftest.py` importa todo `*.models` para construir el esquema de pruebas; este módulo
reexporta los modelos de idempotencia y numeración usados por toda la Fase 3.
"""

from sistemashn.comercial import idempotency, sequences

__all__ = ["idempotency", "sequences"]
