"""Pruebas de `build_context`: base de datos, módulos y servicios registrados (T1.6b-1)."""

from __future__ import annotations

from datetime import UTC, datetime

from sistemashn.app.bootstrap import build_context

FIXED_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def _clock() -> datetime:
    return FIXED_NOW


def test_build_context_crea_base_y_registra_servicios(tmp_path):
    carpeta = tmp_path / "datos"

    ctx = build_context(
        carpeta, vertical="repuestos", clock=_clock, fingerprint_fn=lambda: "f" * 64
    )

    assert (carpeta / "sistemashn.db").exists()
    assert ctx.data_dir == carpeta

    esperados = {
        "identity",
        "recovery",
        "permissions",
        "audit",
        "settings",
        "setup",
        "license",
    }
    assert esperados <= ctx.services.keys()

    # El registro de módulos (Core + Comercial + Repuestos) valida sin errores.
    ctx.registry.validate()
    assert {"core", "comercial", "repuestos"} <= ctx.registry.module_codes()


def test_build_context_es_reentrante(tmp_path):
    carpeta = tmp_path / "datos"

    primero = build_context(carpeta, vertical="repuestos", clock=_clock)
    segundo = build_context(carpeta, vertical="repuestos", clock=_clock)

    # Misma base de datos: el segundo arranque no recrea la instalación.
    estado1 = primero.services["setup"].state()
    estado2 = segundo.services["setup"].state()
    assert estado1.installation_id == estado2.installation_id
