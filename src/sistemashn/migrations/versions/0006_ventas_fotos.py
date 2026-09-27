"""ventas_fotos

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-27

Lista de control de tablas/columnas cubiertas:
- com_product.image_path (Fase 7, T7.4) <- comercial/catalogo/models.py
- com_sale_line.backorder_qty (Fase 7, T7.3) <- comercial/ventas/models.py
- com_customer_return: sale_line_id ahora nullable + product_id/unit_price_override
  (Fase 7, T7.3, devolución "sin comprobante") <- comercial/devoluciones/models.py
- com_supplier_return: purchase_line_id ahora nullable + product_id/unit_price_override
  (Fase 7, T7.3, devolución "sin comprobante") <- comercial/devoluciones/models.py
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _com_customer_return_table(sale_line_id_nullable: bool) -> sa.Table:
    """Forma de `com_customer_return` (sin `product_id`/`unit_price_override`, como en 0004)."""
    return sa.Table(
        "com_customer_return",
        sa.MetaData(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_line_id", sa.Integer(), nullable=sale_line_id_nullable),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(length=20), nullable=False),
        sa.Column("resolution", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("new_sale_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "condition IN ('vendible', 'no_vendible')",
            name=op.f("ck_com_customer_return_condition_valida"),
        ),
        sa.CheckConstraint(
            "resolution IN ('reembolso', 'cambio', 'saldo_a_favor')",
            name=op.f("ck_com_customer_return_resolution_valida"),
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


def _com_customer_return_table_actualizada() -> sa.Table:
    """Forma ya con `product_id`/`unit_price_override` (para el `copy_from` de downgrade)."""
    tabla = _com_customer_return_table(sale_line_id_nullable=True)
    tabla.append_column(sa.Column("product_id", sa.Integer(), nullable=True))
    tabla.append_column(sa.Column("unit_price_override", sa.Integer(), nullable=True))
    tabla.append_constraint(
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_com_customer_return_product_id_com_product"),
        )
    )
    tabla.append_constraint(
        sa.CheckConstraint(
            "sale_line_id IS NOT NULL "
            "OR (product_id IS NOT NULL AND unit_price_override IS NOT NULL)",
            name=op.f("ck_com_customer_return_sin_comprobante_valida"),
        )
    )
    return tabla


def _com_supplier_return_table(purchase_line_id_nullable: bool) -> sa.Table:
    """Forma de `com_supplier_return` (sin `product_id`/`unit_price_override`, como en 0004)."""
    return sa.Table(
        "com_supplier_return",
        sa.MetaData(),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_line_id", sa.Integer(), nullable=purchase_line_id_nullable),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("resolution", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "resolution IN ('reemplazo', 'reembolso', 'credito_futuro')",
            name=op.f("ck_com_supplier_return_resolution_valida"),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_line_id"],
            ["com_purchase_line.id"],
            name=op.f("fk_com_supplier_return_purchase_line_id_com_purchase_line"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_supplier_return")),
    )


def _com_supplier_return_table_actualizada() -> sa.Table:
    """Forma ya con `product_id`/`unit_price_override` (para el `copy_from` de downgrade)."""
    tabla = _com_supplier_return_table(purchase_line_id_nullable=True)
    tabla.append_column(sa.Column("product_id", sa.Integer(), nullable=True))
    tabla.append_column(sa.Column("unit_price_override", sa.Integer(), nullable=True))
    tabla.append_constraint(
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_com_supplier_return_product_id_com_product"),
        )
    )
    tabla.append_constraint(
        sa.CheckConstraint(
            "purchase_line_id IS NOT NULL "
            "OR (product_id IS NOT NULL AND unit_price_override IS NOT NULL)",
            name=op.f("ck_com_supplier_return_sin_comprobante_valida"),
        )
    )
    return tabla


def upgrade() -> None:
    op.add_column("com_product", sa.Column("image_path", sa.String(), nullable=True))

    op.add_column(
        "com_sale_line",
        sa.Column("backorder_qty", sa.Integer(), nullable=False, server_default="0"),
    )

    with op.batch_alter_table(
        "com_customer_return",
        copy_from=_com_customer_return_table(sale_line_id_nullable=False),
        recreate="always",
    ) as batch_op:
        batch_op.alter_column("sale_line_id", nullable=True)
        batch_op.add_column(sa.Column("product_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("unit_price_override", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_com_customer_return_product_id_com_product"),
            "com_product",
            ["product_id"],
            ["id"],
        )
        batch_op.create_check_constraint(
            op.f("ck_com_customer_return_sin_comprobante_valida"),
            "sale_line_id IS NOT NULL "
            "OR (product_id IS NOT NULL AND unit_price_override IS NOT NULL)",
        )

    with op.batch_alter_table(
        "com_supplier_return",
        copy_from=_com_supplier_return_table(purchase_line_id_nullable=False),
        recreate="always",
    ) as batch_op:
        batch_op.alter_column("purchase_line_id", nullable=True)
        batch_op.add_column(sa.Column("product_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("unit_price_override", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_com_supplier_return_product_id_com_product"),
            "com_product",
            ["product_id"],
            ["id"],
        )
        batch_op.create_check_constraint(
            op.f("ck_com_supplier_return_sin_comprobante_valida"),
            "purchase_line_id IS NOT NULL "
            "OR (product_id IS NOT NULL AND unit_price_override IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "com_supplier_return",
        copy_from=_com_supplier_return_table_actualizada(),
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            op.f("ck_com_supplier_return_sin_comprobante_valida"), type_="check"
        )
        batch_op.drop_constraint(
            op.f("fk_com_supplier_return_product_id_com_product"), type_="foreignkey"
        )
        batch_op.drop_column("unit_price_override")
        batch_op.drop_column("product_id")
        batch_op.alter_column("purchase_line_id", nullable=False)

    with op.batch_alter_table(
        "com_customer_return",
        copy_from=_com_customer_return_table_actualizada(),
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            op.f("ck_com_customer_return_sin_comprobante_valida"), type_="check"
        )
        batch_op.drop_constraint(
            op.f("fk_com_customer_return_product_id_com_product"), type_="foreignkey"
        )
        batch_op.drop_column("unit_price_override")
        batch_op.drop_column("product_id")
        batch_op.alter_column("sale_line_id", nullable=False)

    op.drop_column("com_sale_line", "backorder_qty")
    op.drop_column("com_product", "image_path")
