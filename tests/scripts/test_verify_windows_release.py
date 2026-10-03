"""El paquete compilado debe contener migraciones que Alembic pueda ejecutar."""

import shutil
from pathlib import Path

import pytest
from scripts.verify_windows_release import verify_release

SOURCE_MIGRATIONS = Path(__file__).resolve().parents[2] / "src/sistemashn/migrations"


def _release(tmp_path: Path) -> Path:
    release = tmp_path / "release"
    migrations = release / "app/sistemashn/migrations"
    shutil.copytree(SOURCE_MIGRATIONS, migrations, ignore=shutil.ignore_patterns("__pycache__"))
    (release / "sistemashn.exe").touch()
    return release


def test_release_migrations_create_installation_table(tmp_path: Path) -> None:
    release = _release(tmp_path)

    assert verify_release(release) == "0009"


def test_release_rejects_bytecode_only_migrations(tmp_path: Path) -> None:
    release = _release(tmp_path)
    for revision in (release / "app/sistemashn/migrations/versions").glob("*.py"):
        revision.unlink()

    with pytest.raises(ValueError, match=r"migraciones \.py"):
        verify_release(release)
