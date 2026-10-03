"""Ficha y presentaciones de Ferretería.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fer_item",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("family", sa.String(length=100), nullable=True),
        sa.Column("specs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"], ["com_product.id"], name=op.f("fk_fer_item_product_id_com_product")
        ),
        sa.PrimaryKeyConstraint("product_id", name=op.f("pk_fer_item")),
    )
    op.create_index(op.f("ix_fer_item_brand"), "fer_item", ["brand"])
    op.create_index(op.f("ix_fer_item_family"), "fer_item", ["family"])

    op.create_table(
        "fer_pack",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("factor_numerator", sa.Integer(), nullable=False),
        sa.Column("factor_denominator", sa.Integer(), nullable=False),
        sa.Column("permits_fraction", sa.Boolean(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "factor_numerator > 0", name=op.f("ck_fer_pack_factor_numerator_positivo")
        ),
        sa.CheckConstraint(
            "factor_denominator > 0", name=op.f("ck_fer_pack_factor_denominator_positivo")
        ),
        sa.CheckConstraint(
            "price IS NULL OR price >= 0", name=op.f("ck_fer_pack_price_no_negativo")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["com_product.id"], name=op.f("fk_fer_pack_product_id_com_product")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fer_pack")),
        sa.UniqueConstraint("product_id", "label", name="uq_fer_pack_product_label"),
        sa.UniqueConstraint("code", name=op.f("uq_fer_pack_code")),
    )
    op.create_index(op.f("ix_fer_pack_product_id"), "fer_pack", ["product_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_fer_pack_product_id"), table_name="fer_pack")
    op.drop_table("fer_pack")
    op.drop_index(op.f("ix_fer_item_family"), table_name="fer_item")
    op.drop_index(op.f("ix_fer_item_brand"), table_name="fer_item")
    op.drop_table("fer_item")
