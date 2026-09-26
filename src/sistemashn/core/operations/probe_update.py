"""Actualizador local de ensayo, invocado con la aplicación cerrada."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL

from .backup import _integrity, _revision, _sha256, _snapshot
from .contracts import UpdateError, UpdateResult


def _package(path: Path) -> tuple[dict, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            if set(archive.namelist()) != {"manifest.json", "app.bin"}:
                raise UpdateError("El ZIP debe contener sólo manifest.json y app.bin")
            if archive.getinfo("app.bin").file_size > 512 * 1024 * 1024 or archive.getinfo("manifest.json").file_size > 64 * 1024:
                raise UpdateError("Paquete demasiado grande")
            manifest = json.loads(archive.read("manifest.json"))
            binary = archive.read("app.bin")
    except (OSError, zipfile.BadZipFile, ValueError, KeyError) as exc:
        raise UpdateError(f"ZIP inválido: {exc}") from exc
    if not isinstance(manifest, dict) or set(manifest) != {"format", "from_version", "to_version", "app_sha256"} or manifest["format"] != 1:
        raise UpdateError("Manifiesto inválido")
    if not all(isinstance(manifest[key], str) and manifest[key] for key in ("from_version", "to_version", "app_sha256")):
        raise UpdateError("Versiones o hash inválidos")
    if not binary or hashlib.sha256(binary).hexdigest() != manifest["app_sha256"]:
        raise UpdateError("Hash de app.bin inválido")
    return manifest, binary


def _migrate(path: Path) -> None:
    root = Path(__file__).resolve().parents[4]
    config = Config(str(root / "alembic.ini"))
    url = URL.create("sqlite", database=str(path.resolve())).render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "0002")


def _startup_probe(app: Path, data_dir: Path) -> None:
    if not app.is_file() or not app.stat().st_size:
        raise UpdateError("Binario de sonda vacío")
    database = data_dir / "probe.sqlite3"
    if not _integrity(database) or _revision(database) != "0002":
        raise UpdateError("La base no arranca en la revisión 0002")
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("SELECT id, value, note FROM probe_records LIMIT 1").fetchall()


def _replace_closed(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def apply_probe_update(package: Path, installation: Path, data_dir: Path) -> UpdateResult:
    """Ensaya y publica la actualización de la sonda con la app cerrada.

    No sustituye el formato firmado ni protege de un corte eléctrico a mitad
    de los tres reemplazos. Se requiere comprobación de arranque al reiniciar.
    """
    app = installation / "app.bin"
    version = installation / "version.json"
    database = data_dir / "probe.sqlite3"
    if not all(path.is_file() for path in (app, version, database)):
        raise UpdateError("Instalación incompleta")
    manifest, binary = _package(package)
    try:
        previous = json.loads(version.read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise UpdateError("Versión instalada inválida") from exc
    if manifest["from_version"] != previous or previous == manifest["to_version"]:
        raise UpdateError("La versión origen no coincide o no hay cambio")
    if _revision(database) != "0001" or not _integrity(database):
        raise UpdateError("La base origen debe estar íntegra en 0001")

    # Cada área se prepara en el mismo volumen que su destino (Windows/NTFS).
    with tempfile.TemporaryDirectory(prefix=".update-app-", dir=installation) as install_tmp, tempfile.TemporaryDirectory(prefix=".update-data-", dir=data_dir) as data_tmp:
        install_stage = Path(install_tmp)
        data_stage = Path(data_tmp)
        staged_app = install_stage / "app.bin"
        staged_version = install_stage / "version.json"
        staged_data = data_stage / "data"
        staged_data.mkdir()
        staged_db = staged_data / "probe.sqlite3"
        old_app = install_stage / "old-app.bin"
        old_version = install_stage / "old-version.json"
        old_db = data_stage / "old-probe.sqlite3"

        staged_app.write_bytes(binary)
        staged_version.write_text(json.dumps({"version": manifest["to_version"]}), encoding="utf-8")
        shutil.copy2(app, old_app)
        shutil.copy2(version, old_version)
        _snapshot(database, old_db)
        if not _integrity(old_db):
            raise UpdateError("Respaldo previo no íntegro")
        _snapshot(database, staged_db)
        try:
            _migrate(staged_db)
            if _revision(staged_db) != "0002" or not _integrity(staged_db):
                raise UpdateError("Migración incompleta")
            _startup_probe(staged_app, staged_data)
        except Exception as exc:
            raise UpdateError(f"Ensayo rechazado: {exc}") from exc

        try:
            _replace_closed(staged_app, app)
            _replace_closed(staged_version, version)
            _replace_closed(staged_db, database)
            _startup_probe(app, data_dir)
        except Exception as exc:
            try:
                _replace_closed(old_app, app)
                _replace_closed(old_version, version)
                _replace_closed(old_db, database)
            except Exception as rollback_exc:
                raise UpdateError(f"Fallo al publicar y restaurar: {exc}; {rollback_exc}; inspeccionar {install_tmp} y {data_tmp}") from rollback_exc
            raise UpdateError(f"Actualización revertida: {exc}") from exc
    return UpdateResult(installation, data_dir, previous, manifest["to_version"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Sonda de actualización local; cierre la aplicación antes de ejecutar")
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--installation", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    result = apply_probe_update(args.package, args.installation, args.data_dir)
    print(f"Actualización de sonda {result.previous_version} → {result.installed_version}")


if __name__ == "__main__":
    main()
