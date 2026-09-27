"""Actualización local de ensayo por paquete ZIP con reversión coherente (T0.4).

Un paquete de actualización es un ZIP con `manifest.json` en la raíz y los archivos
del programa bajo `payload/<ruta>`. `apply_probe_update` valida el paquete, respalda
la instalación y la base de datos, aplica los cambios y migra el esquema; si algo
falla revierte tanto el programa como la base a su estado previo.

Supuesto: ningún proceso tiene la base de datos abierta durante la actualización
(el actualizador real de Fase 6 esperará a que la aplicación cierre antes de invocar
esta función). Ver `docs/decisions/003-contrato-recuperacion-etapa0.md`.
"""

import hashlib
import json
import os
import re
import shutil
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from sistemashn.core.db import migrate
from sistemashn.core.operations.backup import create_backup, verify_backup
from sistemashn.core.operations.contracts import OperationError
from sistemashn.core.operations.restore import restore_to_trial

_PAYLOAD_PREFIX = "payload/"
_MANIFEST_NAME = "manifest.json"
_DRIVE_LETTER_RE = re.compile(r"^[A-Za-z]:")


class InvalidPackageError(OperationError):
    """El paquete de actualización es ilegible, está malformado o no es aplicable."""


@dataclass(frozen=True)
class UpdateManifest:
    """Metadatos declarados por un paquete de actualización."""

    format: int
    version: str
    min_from_version: str
    schema_revision: str
    files: dict[str, str]


@dataclass(frozen=True)
class UpdateResult:
    """Resultado de aplicar (o intentar aplicar) un paquete de actualización."""

    ok: bool
    from_version: str
    to_version: str
    error: str | None
    rolled_back: bool


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _parse_version(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except (ValueError, AttributeError) as exc:
        raise InvalidPackageError(f"versión inválida: {value!r}") from exc


def _check_safe_relpath(relpath: str) -> None:
    if not relpath or relpath != relpath.strip():
        raise InvalidPackageError(f"ruta inválida en manifest: {relpath!r}")
    if "\\" in relpath:
        raise InvalidPackageError(f"ruta con backslash no permitida: {relpath!r}")
    if _DRIVE_LETTER_RE.match(relpath):
        raise InvalidPackageError(f"ruta con letra de unidad no permitida: {relpath!r}")
    pure = PurePosixPath(relpath)
    if pure.is_absolute():
        raise InvalidPackageError(f"ruta absoluta no permitida: {relpath!r}")
    parts = pure.parts
    if not parts or ".." in parts or "." in parts:
        raise InvalidPackageError(f"ruta con path traversal no permitida: {relpath!r}")


def _open_zip(package: Path) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(package)
    except (zipfile.BadZipFile, FileNotFoundError, OSError) as exc:
        raise InvalidPackageError(f"ZIP ilegible ({package}): {exc}") from exc


def _parse_manifest(zf: zipfile.ZipFile) -> UpdateManifest:
    try:
        raw = zf.read(_MANIFEST_NAME)
    except KeyError as exc:
        raise InvalidPackageError("manifest.json ausente en el paquete") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidPackageError(f"manifest.json malformado: {exc}") from exc

    if not isinstance(data, dict):
        raise InvalidPackageError("manifest.json malformado: no es un objeto")

    try:
        fmt = int(data["format"])
        version = str(data["version"])
        min_from_version = str(data["min_from_version"])
        schema_revision = str(data["schema_revision"])
        files_raw = data["files"]
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidPackageError(f"manifest.json malformado: {exc}") from exc

    if not isinstance(files_raw, dict):
        raise InvalidPackageError("manifest.json malformado: 'files' debe ser un objeto")

    if fmt != 1:
        raise InvalidPackageError(f"formato de manifest no soportado: {fmt}")

    files = {str(name): str(digest) for name, digest in files_raw.items()}
    return UpdateManifest(
        format=fmt,
        version=version,
        min_from_version=min_from_version,
        schema_revision=schema_revision,
        files=files,
    )


def read_manifest(package: Path) -> UpdateManifest:
    """Lee y parsea el manifest de un paquete de actualización, sin más validación."""
    zf = _open_zip(package)
    try:
        return _parse_manifest(zf)
    finally:
        zf.close()


def validate_package(package: Path, installed_version: str) -> UpdateManifest:
    """Valida por completo un paquete antes de aplicar cualquier cambio en disco.

    Lanza `InvalidPackageError` ante cualquier problema: ZIP ilegible, manifest
    ausente/malformado, formato no soportado, rutas inseguras, archivos faltantes o
    sobrantes en `payload/`, hashes que no coinciden, o versiones incompatibles.
    """
    zf = _open_zip(package)
    try:
        manifest = _parse_manifest(zf)

        for relpath in manifest.files:
            _check_safe_relpath(relpath)

        namelist = set(zf.namelist())
        payload_entries = {
            name[len(_PAYLOAD_PREFIX) :]
            for name in namelist
            if name.startswith(_PAYLOAD_PREFIX) and not name.endswith("/")
        }
        expected = set(manifest.files.keys())

        missing = expected - payload_entries
        if missing:
            raise InvalidPackageError(f"archivos faltantes en payload/: {sorted(missing)}")

        extra = payload_entries - expected
        if extra:
            raise InvalidPackageError(f"archivos no listados en manifest: {sorted(extra)}")

        for relpath, expected_hash in manifest.files.items():
            data = zf.read(f"{_PAYLOAD_PREFIX}{relpath}")
            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != expected_hash:
                raise InvalidPackageError(f"hash inválido para {relpath!r}")

        target_version = _parse_version(manifest.version)
        installed = _parse_version(installed_version)
        min_from = _parse_version(manifest.min_from_version)

        if target_version <= installed:
            raise InvalidPackageError(
                f"la versión del paquete ({manifest.version}) no es mayor que la "
                f"instalada ({installed_version})"
            )
        if installed < min_from:
            raise InvalidPackageError(
                f"la versión instalada ({installed_version}) es menor que "
                f"min_from_version ({manifest.min_from_version})"
            )

        return manifest
    finally:
        zf.close()


def _read_installed_version(installation: Path) -> str:
    return (installation / "VERSION").read_text(encoding="utf-8").strip()


def _extract_payload(package: Path, manifest: UpdateManifest, staging: Path) -> None:
    with zipfile.ZipFile(package) as zf:
        for relpath in manifest.files:
            data = zf.read(f"{_PAYLOAD_PREFIX}{relpath}")
            dest = staging.joinpath(*relpath.split("/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)


def _replace_installation_files(
    staging: Path, installation: Path, manifest: UpdateManifest
) -> None:
    for relpath in manifest.files:
        parts = relpath.split("/")
        source = staging.joinpath(*parts)
        dest = installation.joinpath(*parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_name(dest.name + ".tmp-update")
        shutil.copyfile(source, temp)
        os.replace(temp, dest)

    version_path = installation / "VERSION"
    temp_version = version_path.with_name(version_path.name + ".tmp-update")
    temp_version.write_text(manifest.version, encoding="utf-8")
    os.replace(temp_version, version_path)


def _remove_wal_shm(db_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = db_path.with_name(db_path.name + suffix)
        if sidecar.exists():
            sidecar.unlink()


def _restore_installation(rollback_app: Path, installation: Path) -> None:
    if installation.exists():
        shutil.rmtree(installation)
    shutil.copytree(rollback_app, installation)


def _append_log(work_dir: Path, entry: dict) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    log_path = work_dir / "update-log.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def apply_probe_update(
    package: Path,
    installation: Path,
    db_path: Path,
    work_dir: Path,
    *,
    startup_check: Callable[[Path, Path], None] | None = None,
    clock: Callable[[], datetime] = _default_clock,
) -> UpdateResult:
    """Aplica un paquete de actualización de ensayo con reversión coherente.

    1. Valida el paquete (sin tocar disco); si falla, relanza `InvalidPackageError`
       sin dejar rastro.
    2. Extrae el payload a `work_dir/staging-<ts>/`.
    3. Respalda la instalación completa y la base de datos en `work_dir/rollback-<ts>/`.
    4. Reemplaza los archivos del programa (escritura atómica por archivo) y la
       marca `VERSION`.
    5. Migra el esquema de la base a `manifest.schema_revision`.
    6. Ejecuta `startup_check`, si se proporcionó.
    7. Verifica que la revisión aplicada y la integridad de la base sean correctas.

    Cualquier fallo entre los pasos 4 y 7 revierte tanto el programa como la base al
    estado del respaldo, y el resultado se registra en `work_dir/update-log.jsonl`.
    """
    installed_version = _read_installed_version(installation)
    manifest = validate_package(package, installed_version)

    ts = clock().strftime("%Y%m%dT%H%M%S%f")
    work_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = work_dir / f"staging-{ts}"
    rollback_dir = work_dir / f"rollback-{ts}"
    rollback_app = rollback_dir / "app"
    rollback_db = rollback_dir / "db.sqlite"

    staging_dir.mkdir(parents=True, exist_ok=True)
    _extract_payload(package, manifest, staging_dir)

    rollback_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(installation, rollback_app)
    create_backup(db_path, rollback_db)

    try:
        _replace_installation_files(staging_dir, installation, manifest)
        migrate.upgrade(db_path, manifest.schema_revision)
        if startup_check is not None:
            startup_check(installation, db_path)

        applied_revision = migrate.current_revision(db_path)
        if applied_revision != manifest.schema_revision:
            raise OperationError(
                f"revisión tras migrar ({applied_revision}) no coincide con la "
                f"esperada ({manifest.schema_revision})"
            )
        verification = verify_backup(db_path)
        if not verification.ok:
            raise OperationError(f"verificación final de la base falló: {verification.integrity}")
    except Exception as exc:  # cualquier fallo en 4-7 dispara la reversión completa
        error_message = str(exc)
        _remove_wal_shm(db_path)
        _restore_installation(rollback_app, installation)
        restore_to_trial(rollback_db, db_path, overwrite=True)
        _append_log(
            work_dir,
            {
                "timestamp": clock().isoformat(),
                "from_version": installed_version,
                "to_version": manifest.version,
                "ok": False,
                "rolled_back": True,
                "error": error_message,
            },
        )
        return UpdateResult(
            ok=False,
            from_version=installed_version,
            to_version=manifest.version,
            error=error_message,
            rolled_back=True,
        )

    _append_log(
        work_dir,
        {
            "timestamp": clock().isoformat(),
            "from_version": installed_version,
            "to_version": manifest.version,
            "ok": True,
            "rolled_back": False,
            "error": None,
        },
    )
    return UpdateResult(
        ok=True,
        from_version=installed_version,
        to_version=manifest.version,
        error=None,
        rolled_back=False,
    )
