"""Pruebas de la CLI del proceso `updater` (T6.3)."""

from pathlib import Path

from sistemashn.core.operations.probe_update import UpdateResult
from sistemashn.updater.__main__ import main


def test_main_exito_retorna_0_y_no_relanza(tmp_path: Path, monkeypatch, capsys) -> None:
    resultado = UpdateResult(
        ok=True, from_version="0.1.0", to_version="0.2.0", error=None, rolled_back=False
    )
    monkeypatch.setattr("sistemashn.updater.__main__.run_update", lambda *args, **kwargs: resultado)

    codigo = main(["pkg.zip", "install", "db.sqlite", "work", ".app.lock"])

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "0.1.0 -> 0.2.0" in salida
    assert "manualmente" in salida


def test_main_fallo_retorna_1(tmp_path: Path, monkeypatch, capsys) -> None:
    resultado = UpdateResult(
        ok=False,
        from_version="0.1.0",
        to_version="0.2.0",
        error="la aplicación no cerró a tiempo",
        rolled_back=False,
    )
    monkeypatch.setattr("sistemashn.updater.__main__.run_update", lambda *args, **kwargs: resultado)

    codigo = main(["pkg.zip", "install", "db.sqlite", "work", ".app.lock"])

    salida = capsys.readouterr().out
    assert codigo == 1
    assert "fallida" in salida
    assert "no cerró a tiempo" in salida
