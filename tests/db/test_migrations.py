from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]


def _config(path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    encoded_url = create_engine(f"sqlite:///{path}").url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", encoded_url.replace("%", "%%"))
    return config


def test_upgrade_downgrade_and_reupgrade_preserve_probe_record(tmp_path) -> None:
    path = tmp_path / "Negocio José" / "datos.sqlite3"
    path.parent.mkdir()
    config = _config(path)
    command.upgrade(config, "0001")
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO probe_records (id, value) VALUES (7, 'conservado')"))
        command.upgrade(config, "0002")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT id, value, note FROM probe_records")).one() == (7, "conservado", "")
        command.downgrade(config, "0001")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT id, value FROM probe_records")).one() == (7, "conservado")
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT id, value, note FROM probe_records")).one() == (7, "conservado", "")
    finally:
        engine.dispose()
