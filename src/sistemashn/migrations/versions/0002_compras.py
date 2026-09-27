"""compras

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27

Lista de control de tablas cubiertas (nombre de tabla <- archivo de modelo origen):
- com_purchase, com_purchase_line, com_purchase_payment,
  com_supplier_price <- comercial/compras/models.py
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "com_purchase",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=32), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("supplier_invoice_ref", sa.String(length=60), nullable=True),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("tax_total", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("paid_initial", sa.Integer(), nullable=False),
        sa.Column("credit_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('confirmada', 'anulada')", name="status_valido"),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["com_party.id"], name=op.f("fk_com_purchase_supplier_id_com_party")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_purchase")),
        sa.UniqueConstraint("uuid", name=op.f("uq_com_purchase_uuid")),
        sa.UniqueConstraint("number", name=op.f("uq_com_purchase_number")),
    )

    op.create_table(
        "com_purchase_line",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("description_snapshot", sa.String(length=200), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Integer(), nullable=False),
        sa.Column("line_subtotal", sa.Integer(), nullable=False),
        sa.Column("line_tax", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["com_purchase.id"],
            name=op.f("fk_com_purchase_line_purchase_id_com_purchase"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_com_purchase_line_product_id_com_product"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_purchase_line")),
    )

    op.create_table(
        "com_purchase_payment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=60), nullable=True),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["com_purchase.id"],
            name=op.f("fk_com_purchase_payment_purchase_id_com_purchase"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_purchase_payment")),
    )

    op.create_table(
        "com_supplier_price",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["com_party.id"],
            name=op.f("fk_com_supplier_price_supplier_id_com_party"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_com_supplier_price_product_id_com_product"),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["com_purchase.id"],
            name=op.f("fk_com_supplier_price_purchase_id_com_purchase"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_supplier_price")),
    )


def downgrade() -> None:
    op.drop_table("com_supplier_price")
    op.drop_table("com_purchase_payment")
    op.drop_table("com_purchase_line")
    op.drop_table("com_purchase")
