"""operacion_ui

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27

Lista de control de tablas/columnas cubiertas:
- core_business: columnas nuevas de ajustes de operacion (Fase 7, T7.2) <-
  core/settings/models.py
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ORIGINAL_COLUMNS = (
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("name", sa.String(), nullable=False),
    sa.Column("legal_name", sa.String(), nullable=False),
    sa.Column("rtn", sa.String(length=14), nullable=True),
    sa.Column("address", sa.String(), nullable=False),
    sa.Column("phone", sa.String(), nullable=False),
    sa.Column("email", sa.String(), nullable=False),
    sa.Column("logo_path", sa.String(), nullable=True),
    sa.Column("prices_include_isv", sa.Boolean(), nullable=False),
    sa.Column("fiscal_enabled", sa.Boolean(), nullable=False),
    sa.Column("updated_at", sa.DateTime(), nullable=False),
)


def _original_table() -> sa.Table:
    """Forma de `core_business` tal como la crea `0001_base.py` (sin las columnas de Fase 7)."""
    return sa.Table(
        "core_business",
        sa.MetaData(),
        *_ORIGINAL_COLUMNS,
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_business")),
    )


def _upgraded_table() -> sa.Table:
    """Forma de `core_business` ya con las columnas de Fase 7 (para el `copy_from` de downgrade:
    debe describir el estado ACTUAL de la tabla antes de que batch mode empiece a quitar
    columnas, igual que `_original_table()` describe el estado actual antes de agregarlas)."""
    return sa.Table(
        "core_business",
        sa.MetaData(),
        *_ORIGINAL_COLUMNS,
        sa.Column("cash_session_required", sa.Boolean(), nullable=False),
        sa.Column("block_sale_without_stock", sa.Boolean(), nullable=False),
        sa.Column("print_receipt_policy", sa.String(length=10), nullable=False),
        sa.Column("cashier_sees_own_sales_total", sa.Boolean(), nullable=False),
        sa.Column("max_discount_percent", sa.Integer(), nullable=False),
        sa.Column("default_credit_days", sa.Integer(), nullable=False),
        sa.Column("default_quote_validity_days", sa.Integer(), nullable=False),
        sa.Column("pos_simplified_mode_enabled", sa.Boolean(), nullable=False),
        sa.Column("pos_exit_requires_manager_auth", sa.Boolean(), nullable=False),
        sa.Column("show_logo_in_app", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "print_receipt_policy IN ('auto', 'ask', 'never')",
            name=op.f("ck_core_business_print_receipt_policy_valida"),
        ),
        sa.CheckConstraint(
            "default_credit_days > 0",
            name=op.f("ck_core_business_default_credit_days_positivo"),
        ),
        sa.CheckConstraint(
            "default_quote_validity_days > 0",
            name=op.f("ck_core_business_default_quote_validity_days_positivo"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_business")),
    )


def upgrade() -> None:
    with op.batch_alter_table(
        "core_business", copy_from=_original_table(), recreate="always"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "cash_session_required", sa.Boolean(), nullable=False, server_default=sa.true()
            )
        )
        batch_op.add_column(
            sa.Column(
                "block_sale_without_stock", sa.Boolean(), nullable=False, server_default=sa.true()
            )
        )
        batch_op.add_column(
            sa.Column(
                "print_receipt_policy",
                sa.String(length=10),
                nullable=False,
                server_default="ask",
            )
        )
        batch_op.add_column(
            sa.Column(
                "cashier_sees_own_sales_total",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column("max_discount_percent", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("default_credit_days", sa.Integer(), nullable=False, server_default="30")
        )
        batch_op.add_column(
            sa.Column(
                "default_quote_validity_days", sa.Integer(), nullable=False, server_default="8"
            )
        )
        batch_op.add_column(
            sa.Column(
                "pos_simplified_mode_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "pos_exit_requires_manager_auth",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("show_logo_in_app", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.create_check_constraint(
            op.f("ck_core_business_print_receipt_policy_valida"),
            "print_receipt_policy IN ('auto', 'ask', 'never')",
        )
        batch_op.create_check_constraint(
            op.f("ck_core_business_default_credit_days_positivo"), "default_credit_days > 0"
        )
        batch_op.create_check_constraint(
            op.f("ck_core_business_default_quote_validity_days_positivo"),
            "default_quote_validity_days > 0",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "core_business", copy_from=_upgraded_table(), recreate="always"
    ) as batch_op:
        batch_op.drop_column("show_logo_in_app")
        batch_op.drop_column("pos_exit_requires_manager_auth")
        batch_op.drop_column("pos_simplified_mode_enabled")
        batch_op.drop_column("default_quote_validity_days")
        batch_op.drop_column("default_credit_days")
        batch_op.drop_column("max_discount_percent")
        batch_op.drop_column("cashier_sees_own_sales_total")
        batch_op.drop_column("print_receipt_policy")
        batch_op.drop_column("block_sale_without_stock")
        batch_op.drop_column("cash_session_required")
