"""Migraciones SQLite de la sonda."""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.engine import make_url

from sistemashn.core.db.engine import create_engine_for_path
from sistemashn.core.db.models import Base


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = make_url(config.get_main_option("sqlalchemy.url"))
    if url.get_backend_name() != "sqlite" or not url.database:
        raise ValueError("La sonda requiere una ruta SQLite en sqlalchemy.url")
    engine = create_engine_for_path(Path(url.database))
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
