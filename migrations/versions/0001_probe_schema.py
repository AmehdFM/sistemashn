"""Crear registro de sonda.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "probe_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("value", sa.String(length=200), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("probe_records")
