"""devoluciones

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-27

Lista de control de tablas cubiertas (nombre de tabla <- archivo de modelo origen):
- com_customer_return, com_supplier_return <- comercial/devoluciones/models.py
- com_account.kind: CHECK ampliado a incluir 'credit_note' (saldo a favor) <-
  comercial/credito/models.py
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _com_account_table(kind_check: str) -> sa.Table:
    """Forma de `com_account` tal como la crea `0001_base.py`, con el CHECK de `kind` dado.

    SQLite no soporta ALTER de constraints: `batch_alter_table` necesita conocer la forma
    completa de la tabla (columnas y demás constraints) para poder recrearla; se la damos
    explícita con `copy_from` en vez de depender de que la reflexión detecte los CHECK con
    nombre (SQLite no siempre expone su nombre al reflejar).

    Los nombres de los CHECK aquí son los YA CONVENCIONADOS (`ck_com_account_<nombre>`): en
    `0001_base.py`, `op.create_table` aplica la convención de nombres de `Base.metadata`
    (configurada como `target_metadata` en `env.py`) a cualquier constraint sin `op.f(...)`,
    así que en la base real el CHECK quedó como `ck_com_account_kind_valido`, no
    `kind_valido`. Como aquí construimos la `Table` a mano (no vía `op.create_table`), esa
    conversión automática no ocurre, así que hay que escribir el nombre final nosotros y
    envolverlo en `op.f(...)` para que `batch_alter_table` no intente re-convencionarlo.
    """
    return sa.Table(
        "com_account",
        sa.MetaData(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("party_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=40), nullable=False),
        sa.Column("original_amount", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(kind_check, name=op.f("ck_com_account_kind_valido")),
        sa.CheckConstraint(
            "original_amount > 0", name=op.f("ck_com_account_original_amount_positivo")
        ),
        sa.CheckConstraint("balance >= 0", name=op.f("ck_com_account_balance_no_negativo")),
        sa.CheckConstraint(
            "balance <= original_amount",
            name=op.f("ck_com_account_balance_no_mayor_original"),
        ),
        sa.ForeignKeyConstraint(
            ["party_id"],
            ["com_party.id"],
            name=op.f("fk_com_account_party_id_com_party"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_account")),
        sa.UniqueConstraint("kind", "source_type", "source_id", name=op.f("uq_com_account_source")),
    )


def upgrade() -> None:
    # -- com_account: agrega 'credit_note' (saldo a favor) al CHECK de kind ------------

    tabla_actual = _com_account_table("kind IN ('payable', 'receivable')")
    with op.batch_alter_table("com_account", copy_from=tabla_actual, recreate="always") as batch_op:
        batch_op.drop_constraint(op.f("ck_com_account_kind_valido"), type_="check")
        batch_op.create_check_constraint(
            op.f("ck_com_account_kind_valido"),
            "kind IN ('payable', 'receivable', 'credit_note')",
        )

    # -- Devoluciones -----------------------------------------------------------------

    op.create_table(
        "com_customer_return",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_line_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(length=20), nullable=False),
        sa.Column("resolution", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("new_sale_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("condition IN ('vendible', 'no_vendible')", name="condition_valida"),
        sa.CheckConstraint(
            "resolution IN ('reembolso', 'cambio', 'saldo_a_favor')", name="resolution_valida"
        ),
        sa.ForeignKeyConstraint(
            ["sale_line_id"],
            ["com_sale_line.id"],
            name=op.f("fk_com_customer_return_sale_line_id_com_sale_line"),
        ),
        sa.ForeignKeyConstraint(
            ["new_sale_id"],
            ["com_sale.id"],
            name=op.f("fk_com_customer_return_new_sale_id_com_sale"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_customer_return")),
    )

    op.create_table(
        "com_supplier_return",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_line_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("resolution", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "resolution IN ('reemplazo', 'reembolso', 'credito_futuro')",
            name="resolution_valida",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_line_id"],
            ["com_purchase_line.id"],
            name=op.f("fk_com_supplier_return_purchase_line_id_com_purchase_line"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_supplier_return")),
    )


def downgrade() -> None:
    op.drop_table("com_supplier_return")
    op.drop_table("com_customer_return")

    tabla_ampliada = _com_account_table("kind IN ('payable', 'receivable', 'credit_note')")
    with op.batch_alter_table(
        "com_account", copy_from=tabla_ampliada, recreate="always"
    ) as batch_op:
        batch_op.drop_constraint(op.f("ck_com_account_kind_valido"), type_="check")
        batch_op.create_check_constraint(
            op.f("ck_com_account_kind_valido"), "kind IN ('payable', 'receivable')"
        )
