"""Añadir nota al registro de sonda.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "probe_records",
        sa.Column("note", sa.String(length=200), nullable=False, server_default=sa.text("''")),
    )


def downgrade() -> None:
    with op.batch_alter_table("probe_records") as batch:
        batch.drop_column("note")
