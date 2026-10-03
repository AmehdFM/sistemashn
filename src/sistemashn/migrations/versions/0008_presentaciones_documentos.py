"""Snapshots de presentaciones en líneas de compra y venta.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("com_purchase_line", sa.Column("presentation_snapshot", sa.Text(), nullable=True))
    op.add_column("com_sale_line", sa.Column("presentation_snapshot", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("com_sale_line", "presentation_snapshot")
    op.drop_column("com_purchase_line", "presentation_snapshot")
