"""ventas

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27

Lista de control de tablas cubiertas (nombre de tabla <- archivo de modelo origen):
- com_quote, com_quote_line <- comercial/cotizaciones/models.py
- com_cash_session, com_cash_movement <- comercial/caja/models.py (con triggers append-only)
- com_sale, com_sale_line, com_sale_payment <- comercial/ventas/models.py
- com_fiscal_authorization, com_fiscal_invoice <- comercial/fiscal/models.py
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# -- Disparadores append-only: mismo SQL literal que los modelos --------------------

_CASH_MOVEMENT_TRIGGERS_SQL: tuple[str, ...] = (
    """
    CREATE TRIGGER trg_com_cash_movement_no_update
    BEFORE UPDATE ON com_cash_movement
    BEGIN
        SELECT RAISE(ABORT, 'cash movement is append-only');
    END;
    """,
    """
    CREATE TRIGGER trg_com_cash_movement_no_delete
    BEFORE DELETE ON com_cash_movement
    BEGIN
        SELECT RAISE(ABORT, 'cash movement is append-only');
    END;
    """,
)


def upgrade() -> None:
    # -- Cotizaciones -----------------------------------------------------------------

    op.create_table(
        "com_quote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=32), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("has_reservation", sa.Boolean(), nullable=False),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("tax_total", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('abierta', 'convertida', 'cancelada', 'vencida')", name="status_valido"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["com_party.id"], name=op.f("fk_com_quote_customer_id_com_party")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_quote")),
        sa.UniqueConstraint("uuid", name=op.f("uq_com_quote_uuid")),
        sa.UniqueConstraint("number", name=op.f("uq_com_quote_number")),
    )

    op.create_table(
        "com_quote_line",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("description_snapshot", sa.String(length=200), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Integer(), nullable=False),
        sa.Column("line_subtotal", sa.Integer(), nullable=False),
        sa.Column("line_tax", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["quote_id"], ["com_quote.id"], name=op.f("fk_com_quote_line_quote_id_com_quote")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_com_quote_line_product_id_com_product"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_quote_line")),
    )

    # -- Caja ---------------------------------------------------------------------

    op.create_table(
        "com_cash_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("opened_by", sa.Integer(), nullable=False),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("opening_amount", sa.Integer(), nullable=False),
        sa.Column("expected_cash", sa.Integer(), nullable=True),
        sa.Column("counted_cash", sa.Integer(), nullable=True),
        sa.Column("difference", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('abierta', 'cerrada')", name="status_valido"),
        sa.CheckConstraint("opening_amount >= 0", name="opening_amount_no_negativo"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_cash_session")),
    )

    op.create_table(
        "com_cash_movement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cash_session_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ref_type", sa.String(length=40), nullable=True),
        sa.Column("ref_id", sa.String(length=40), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('entrada', 'salida', 'venta', 'abono')", name="kind_valido"),
        sa.CheckConstraint("amount > 0", name="amount_positivo"),
        sa.ForeignKeyConstraint(
            ["cash_session_id"],
            ["com_cash_session.id"],
            name=op.f("fk_com_cash_movement_cash_session_id_com_cash_session"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_cash_movement")),
    )
    for _sql in _CASH_MOVEMENT_TRIGGERS_SQL:
        op.execute(_sql)

    # -- Ventas ---------------------------------------------------------------------

    op.create_table(
        "com_sale",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=32), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("sold_at", sa.DateTime(), nullable=False),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("tax_total", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("paid_amount", sa.Integer(), nullable=False),
        sa.Column("change_amount", sa.Integer(), nullable=False),
        sa.Column("credit_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cash_session_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('confirmada', 'anulada')", name="status_valido"),
        sa.ForeignKeyConstraint(
            ["quote_id"], ["com_quote.id"], name=op.f("fk_com_sale_quote_id_com_quote")
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["com_party.id"], name=op.f("fk_com_sale_customer_id_com_party")
        ),
        sa.ForeignKeyConstraint(
            ["cash_session_id"],
            ["com_cash_session.id"],
            name=op.f("fk_com_sale_cash_session_id_com_cash_session"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_sale")),
        sa.UniqueConstraint("uuid", name=op.f("uq_com_sale_uuid")),
        sa.UniqueConstraint("number", name=op.f("uq_com_sale_number")),
    )

    op.create_table(
        "com_sale_line",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("description_snapshot", sa.String(length=200), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Integer(), nullable=False),
        sa.Column("line_subtotal", sa.Integer(), nullable=False),
        sa.Column("line_tax", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Integer(), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Integer(), nullable=False),
        sa.Column("kit_component_of", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["com_sale.id"], name=op.f("fk_com_sale_line_sale_id_com_sale")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_com_sale_line_product_id_com_product"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_sale_line")),
    )

    op.create_table(
        "com_sale_payment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=60), nullable=True),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["com_sale.id"], name=op.f("fk_com_sale_payment_sale_id_com_sale")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_sale_payment")),
    )

    # -- Fiscal (CAI) ---------------------------------------------------------------

    op.create_table(
        "com_fiscal_authorization",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cai", sa.String(length=37), nullable=False),
        sa.Column("document_type", sa.String(length=20), nullable=False),
        sa.Column("range_start", sa.String(length=20), nullable=False),
        sa.Column("range_end", sa.String(length=20), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("next_correlative", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint("document_type IN ('factura')", name="document_type_valido"),
        sa.CheckConstraint(
            "status IN ('activa', 'agotada', 'vencida')", name="fiscal_status_valido"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_fiscal_authorization")),
        sa.UniqueConstraint("cai", name=op.f("uq_com_fiscal_authorization_cai")),
    )

    op.create_table(
        "com_fiscal_invoice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("authorization_id", sa.Integer(), nullable=False),
        sa.Column("fiscal_number", sa.String(length=20), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["authorization_id"],
            ["com_fiscal_authorization.id"],
            name=op.f("fk_com_fiscal_invoice_authorization_id_com_fiscal_authorization"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_fiscal_invoice")),
        sa.UniqueConstraint("sale_id", name=op.f("uq_com_fiscal_invoice_sale_id")),
        sa.UniqueConstraint("fiscal_number", name=op.f("uq_com_fiscal_invoice_fiscal_number")),
    )


def downgrade() -> None:
    op.drop_table("com_fiscal_invoice")
    op.drop_table("com_fiscal_authorization")

    op.drop_table("com_sale_payment")
    op.drop_table("com_sale_line")
    op.drop_table("com_sale")

    op.execute("DROP TRIGGER trg_com_cash_movement_no_delete")
    op.execute("DROP TRIGGER trg_com_cash_movement_no_update")
    op.drop_table("com_cash_movement")
    op.drop_table("com_cash_session")

    op.drop_table("com_quote_line")
    op.drop_table("com_quote")
