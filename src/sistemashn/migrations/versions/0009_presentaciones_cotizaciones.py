"""Snapshot de presentación en cotizaciones.

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("com_quote_line", sa.Column("presentation_snapshot", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("com_quote_line", "presentation_snapshot")
