"""Comprueba que el paquete Windows puede crear el esquema de una base nueva."""

import argparse
import os
import sqlite3
import subprocess
import tempfile
import time
from contextlib import closing
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


def verify_release(release: Path) -> str:
    """Migra una base temporal usando las revisiones incluidas en `release`."""
    release = Path(release)
    if not (release / "sistemashn.exe").is_file():
        raise ValueError(f"Falta sistemashn.exe en {release}")

    migrations = release / "app/sistemashn/migrations"
    if not list((migrations / "versions").glob("[0-9]*.py")):
        raise ValueError(f"Faltan migraciones .py en {migrations / 'versions'}")

    with tempfile.TemporaryDirectory(prefix="sistemashn-release-") as temp:
        db = Path(temp) / "sistemashn.db"
        cfg = Config()
        cfg.set_main_option("script_location", str(migrations.resolve()))
        cfg.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db}")
        heads = ScriptDirectory.from_config(cfg).get_heads()
        if len(heads) != 1:
            raise ValueError(f"Se esperaba una revisión final, se encontraron: {heads}")
        command.upgrade(cfg, "head")

        with closing(sqlite3.connect(db)) as connection:
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        if "core_installation" not in tables or revision != (heads[0],):
            raise ValueError("El paquete no creó core_installation en la revisión final")
        return heads[0]


def smoke_release(release: Path, timeout_seconds: int = 40) -> None:
    """Abre el .exe con datos aislados y espera a que termine su primer arranque."""
    release = Path(release).resolve()
    with tempfile.TemporaryDirectory(prefix="sistemashn-smoke-") as temp:
        db = Path(temp) / "sistemashn.db"
        env = os.environ.copy()
        env["SISTEMASHN_DATA_DIR"] = temp
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        process = subprocess.Popen(
            [str(release / "sistemashn.exe")],
            cwd=release,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startup,
        )
        try:
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                if db.exists():
                    try:
                        with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as connection:
                            count = connection.execute(
                                "SELECT COUNT(*) FROM core_installation"
                            ).fetchone()
                        if count and count[0] == 1:
                            return
                    except sqlite3.Error:
                        pass  # La migración todavía puede estar en curso.
                if process.poll() is not None:
                    break
                time.sleep(0.5)
            _, stderr = process.communicate(timeout=5) if process.poll() is not None else (b"", b"")
            raise RuntimeError(
                "El ejecutable no completó el primer arranque con una base nueva. "
                f"Salida: {stderr.decode(errors='replace')[-2000:]}"
            )
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument(
        "--smoke", action="store_true", help="Arranca el ejecutable con datos aislados"
    )
    args = parser.parse_args()
    revision = verify_release(args.release)
    print(f"Paquete verificado: esquema {revision} y core_installation")
    if args.smoke:
        smoke_release(args.release)
        print("Ejecutable verificado: primer arranque Windows con base nueva")


if __name__ == "__main__":
    main()
