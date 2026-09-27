"""esquema base

Revision ID: 0001
Revises:
Create Date: 2026-09-27

Lista de control de tablas cubiertas (nombre de tabla <- archivo de modelo origen):
- core_audit_event <- core/audit/models.py (con triggers append-only)
- core_user_permission <- core/authorization/models.py
- core_user, core_login_session, core_auth_failure, core_recovery_code,
  core_recovery_challenge <- core/identity/models.py
- core_license <- core/licensing/models.py
- core_business, core_setting <- core/settings/models.py
- core_installation <- core/setup/models.py
- com_unit, com_category, com_product <- comercial/catalogo/models.py
- com_kit_component <- comercial/catalogo/kits.py
- com_party <- comercial/contrapartes/models.py
- com_account, com_account_payment <- comercial/credito/models.py (con triggers append-only)
- com_stock, com_stock_movement <- comercial/inventario/models.py (con triggers append-only)
- com_idempotency <- comercial/idempotency.py
- com_sequence <- comercial/sequences.py
- rep_equivalence_group, rep_part <- repuestos/partes/models.py
- rep_vehicle_make, rep_vehicle_model, rep_compatibility <- repuestos/vehiculos/models.py
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# -- Disparadores append-only: mismo SQL literal que los modelos --------------------

_AUDIT_TRIGGERS_SQL: tuple[str, ...] = (
    """
    CREATE TRIGGER trg_core_audit_event_no_update
    BEFORE UPDATE ON core_audit_event
    BEGIN
        SELECT RAISE(ABORT, 'audit is append-only');
    END;
    """,
    """
    CREATE TRIGGER trg_core_audit_event_no_delete
    BEFORE DELETE ON core_audit_event
    BEGIN
        SELECT RAISE(ABORT, 'audit is append-only');
    END;
    """,
)

_ACCOUNT_PAYMENT_TRIGGERS_SQL: tuple[str, ...] = (
    """
    CREATE TRIGGER trg_com_account_payment_no_update
    BEFORE UPDATE ON com_account_payment
    BEGIN
        SELECT RAISE(ABORT, 'account payment is append-only');
    END;
    """,
    """
    CREATE TRIGGER trg_com_account_payment_no_delete
    BEFORE DELETE ON com_account_payment
    BEGIN
        SELECT RAISE(ABORT, 'account payment is append-only');
    END;
    """,
)

_STOCK_MOVEMENT_TRIGGERS_SQL: tuple[str, ...] = (
    """
    CREATE TRIGGER trg_com_stock_movement_no_update
    BEFORE UPDATE ON com_stock_movement
    BEGIN
        SELECT RAISE(ABORT, 'stock movement is append-only');
    END;
    """,
    """
    CREATE TRIGGER trg_com_stock_movement_no_delete
    BEFORE DELETE ON com_stock_movement
    BEGIN
        SELECT RAISE(ABORT, 'stock movement is append-only');
    END;
    """,
)


def upgrade() -> None:
    # -- Core -----------------------------------------------------------------------

    op.create_table(
        "core_audit_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_audit_event")),
    )
    op.create_index(op.f("ix_core_audit_event_occurred_at"), "core_audit_event", ["occurred_at"])
    op.create_index(op.f("ix_core_audit_event_action"), "core_audit_event", ["action"])
    op.create_index("ix_core_audit_event_entity", "core_audit_event", ["entity_type", "entity_id"])
    for _sql in _AUDIT_TRIGGERS_SQL:
        op.execute(_sql)

    op.create_table(
        "core_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("profile_code", sa.String(), nullable=True),
        sa.Column("permissions_version", sa.Integer(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_user")),
        sa.UniqueConstraint("username", name=op.f("uq_core_user_username")),
    )

    op.create_table(
        "core_user_permission",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission_code", sa.String(), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core_user.id"],
            name=op.f("fk_core_user_permission_user_id_core_user"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "permission_code", name=op.f("pk_core_user_permission")),
    )

    op.create_table(
        "core_login_session",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["core_user.id"], name=op.f("fk_core_login_session_user_id_core_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_login_session")),
    )

    op.create_table(
        "core_auth_failure",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username_intentado", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_auth_failure")),
    )

    op.create_table(
        "core_recovery_code",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("used_by_user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_recovery_code")),
    )

    op.create_table(
        "core_recovery_challenge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nonce", sa.String(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_recovery_challenge")),
        sa.UniqueConstraint("nonce", name=op.f("uq_core_recovery_challenge_nonce")),
    )

    op.create_table(
        "core_license",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=False),
        sa.Column("license_id", sa.String(), nullable=False),
        sa.Column("installed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_license")),
    )

    op.create_table(
        "core_business",
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_business")),
    )

    op.create_table(
        "core_setting",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_core_setting")),
    )

    op.create_table(
        "core_installation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("installation_id", sa.String(), nullable=False),
        sa.Column("vertical", sa.String(), nullable=False),
        sa.Column("setup_step", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_installation")),
    )

    # -- Comercial --------------------------------------------------------------------

    op.create_table(
        "com_unit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("allows_fraction", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_unit")),
        sa.UniqueConstraint("code", name=op.f("uq_com_unit_code")),
    )

    op.create_table(
        "com_category",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_category")),
        sa.UniqueConstraint("name", name=op.f("uq_com_category_name")),
    )

    op.create_table(
        "com_product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_search", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Integer(), nullable=False),
        sa.Column("sale_price", sa.Integer(), nullable=False),
        sa.Column("min_stock", sa.Integer(), nullable=False),
        sa.Column("is_kit", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("sale_price >= 0", name="sale_price_no_negativo"),
        sa.CheckConstraint("tax_rate IN (0, 1500, 1800)", name="tax_rate_valido"),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["com_category.id"],
            name=op.f("fk_com_product_category_id_com_category"),
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["com_unit.id"], name=op.f("fk_com_product_unit_id_com_unit")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_product")),
        sa.UniqueConstraint("code", name=op.f("uq_com_product_code")),
        sa.UniqueConstraint("barcode", name=op.f("uq_com_product_barcode")),
    )
    op.create_index(op.f("ix_com_product_name_search"), "com_product", ["name_search"])

    op.create_table(
        "com_kit_component",
        sa.Column("kit_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.CheckConstraint("qty > 0", name="kit_component_qty_positiva"),
        sa.CheckConstraint("kit_id != component_id", name="kit_component_no_autorreferencia"),
        sa.ForeignKeyConstraint(
            ["kit_id"], ["com_product.id"], name=op.f("fk_com_kit_component_kit_id_com_product")
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["com_product.id"],
            name=op.f("fk_com_kit_component_component_id_com_product"),
        ),
        sa.PrimaryKeyConstraint("kit_id", "component_id", name=op.f("pk_com_kit_component")),
    )

    op.create_table(
        "com_party",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_search", sa.String(length=200), nullable=False),
        sa.Column("rtn", sa.String(length=14), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_supplier", sa.Boolean(), nullable=False),
        sa.Column("is_customer", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_party")),
    )
    op.create_index(op.f("ix_com_party_name_search"), "com_party", ["name_search"])
    op.create_index("ix_com_party_rtn", "com_party", ["rtn"])

    op.create_table(
        "com_account",
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
        sa.CheckConstraint("kind IN ('payable', 'receivable')", name="kind_valido"),
        sa.CheckConstraint("original_amount > 0", name="original_amount_positivo"),
        sa.CheckConstraint("balance >= 0", name="balance_no_negativo"),
        sa.CheckConstraint("balance <= original_amount", name="balance_no_mayor_original"),
        sa.ForeignKeyConstraint(
            ["party_id"], ["com_party.id"], name=op.f("fk_com_account_party_id_com_party")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_account")),
        sa.UniqueConstraint("kind", "source_type", "source_id", name="uq_com_account_source"),
    )

    op.create_table(
        "com_account_payment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=60), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.CheckConstraint("amount > 0", name="amount_positivo"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["com_account.id"],
            name=op.f("fk_com_account_payment_account_id_com_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_account_payment")),
        sa.UniqueConstraint("request_id", name=op.f("uq_com_account_payment_request_id")),
    )
    for _sql in _ACCOUNT_PAYMENT_TRIGGERS_SQL:
        op.execute(_sql)

    op.create_table(
        "com_stock",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("on_hand", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.Column("unsellable", sa.Integer(), nullable=False),
        sa.Column("avg_cost", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("on_hand >= 0", name="on_hand_no_negativo"),
        sa.CheckConstraint("reserved >= 0", name="reserved_no_negativo"),
        sa.CheckConstraint("unsellable >= 0", name="unsellable_no_negativo"),
        sa.CheckConstraint("reserved <= on_hand", name="reserved_no_mayor_on_hand"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["com_product.id"], name=op.f("fk_com_stock_product_id_com_product")
        ),
        sa.PrimaryKeyConstraint("product_id", name=op.f("pk_com_stock")),
    )

    op.create_table(
        "com_stock_movement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("d_on_hand", sa.Integer(), nullable=False),
        sa.Column("d_reserved", sa.Integer(), nullable=False),
        sa.Column("d_unsellable", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Integer(), nullable=True),
        sa.Column("avg_cost_after", sa.Integer(), nullable=False),
        sa.Column("ref_type", sa.String(length=40), nullable=True),
        sa.Column("ref_id", sa.String(length=40), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_com_stock_movement_product_id_com_product"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_com_stock_movement")),
    )
    op.create_index("ix_com_stock_movement_product", "com_stock_movement", ["product_id"])
    for _sql in _STOCK_MOVEMENT_TRIGGERS_SQL:
        op.execute(_sql)

    op.create_table(
        "com_idempotency",
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("result_ref", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("request_id", name=op.f("pk_com_idempotency")),
    )

    op.create_table(
        "com_sequence",
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("name", name=op.f("pk_com_sequence")),
    )

    # -- Repuestos ----------------------------------------------------------------

    op.create_table(
        "rep_equivalence_group",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rep_equivalence_group")),
    )

    op.create_table(
        "rep_part",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("part_number", sa.String(length=80), nullable=False),
        sa.Column("part_number_search", sa.String(length=80), nullable=False),
        sa.Column("manufacturer", sa.String(length=120), nullable=True),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("equivalence_group_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("origin IN ('original', 'generico')", name="origin_valido"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_rep_part_product_id_com_product"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["equivalence_group_id"],
            ["rep_equivalence_group.id"],
            name=op.f("fk_rep_part_equivalence_group_id_rep_equivalence_group"),
        ),
        sa.PrimaryKeyConstraint("product_id", name=op.f("pk_rep_part")),
    )
    op.create_index(op.f("ix_rep_part_part_number_search"), "rep_part", ["part_number_search"])
    op.create_index(op.f("ix_rep_part_equivalence_group_id"), "rep_part", ["equivalence_group_id"])

    op.create_table(
        "rep_vehicle_make",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rep_vehicle_make")),
        sa.UniqueConstraint("name", name=op.f("uq_rep_vehicle_make_name")),
    )

    op.create_table(
        "rep_vehicle_model",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("make_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["make_id"],
            ["rep_vehicle_make.id"],
            name=op.f("fk_rep_vehicle_model_make_id_rep_vehicle_make"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rep_vehicle_model")),
        sa.UniqueConstraint("make_id", "name", name="uq_rep_vehicle_model_make_name"),
    )

    op.create_table(
        "rep_compatibility",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("year_from", sa.Integer(), nullable=False),
        sa.Column("year_to", sa.Integer(), nullable=False),
        sa.CheckConstraint("year_from <= year_to", name="year_from_no_mayor_year_to"),
        sa.CheckConstraint("year_from BETWEEN 1950 AND 2100", name="year_from_valido"),
        sa.CheckConstraint("year_to BETWEEN 1950 AND 2100", name="year_to_valido"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["com_product.id"],
            name=op.f("fk_rep_compatibility_product_id_com_product"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["rep_vehicle_model.id"],
            name=op.f("fk_rep_compatibility_model_id_rep_vehicle_model"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rep_compatibility")),
        sa.UniqueConstraint(
            "product_id",
            "model_id",
            "year_from",
            "year_to",
            name="uq_rep_compatibility",
        ),
    )


def downgrade() -> None:
    op.drop_table("rep_compatibility")
    op.drop_table("rep_vehicle_model")
    op.drop_table("rep_vehicle_make")
    op.drop_index(op.f("ix_rep_part_equivalence_group_id"), table_name="rep_part")
    op.drop_index(op.f("ix_rep_part_part_number_search"), table_name="rep_part")
    op.drop_table("rep_part")
    op.drop_table("rep_equivalence_group")

    op.drop_table("com_sequence")
    op.drop_table("com_idempotency")

    op.execute("DROP TRIGGER trg_com_stock_movement_no_delete")
    op.execute("DROP TRIGGER trg_com_stock_movement_no_update")
    op.drop_index("ix_com_stock_movement_product", table_name="com_stock_movement")
    op.drop_table("com_stock_movement")
    op.drop_table("com_stock")

    op.execute("DROP TRIGGER trg_com_account_payment_no_delete")
    op.execute("DROP TRIGGER trg_com_account_payment_no_update")
    op.drop_table("com_account_payment")
    op.drop_table("com_account")

    op.drop_index("ix_com_party_rtn", table_name="com_party")
    op.drop_index(op.f("ix_com_party_name_search"), table_name="com_party")
    op.drop_table("com_party")

    op.drop_table("com_kit_component")

    op.drop_index(op.f("ix_com_product_name_search"), table_name="com_product")
    op.drop_table("com_product")
    op.drop_table("com_category")
    op.drop_table("com_unit")

    op.drop_table("core_installation")
    op.drop_table("core_setting")
    op.drop_table("core_business")
    op.drop_table("core_license")
    op.drop_table("core_recovery_challenge")
    op.drop_table("core_recovery_code")
    op.drop_table("core_auth_failure")
    op.drop_table("core_login_session")
    op.drop_table("core_user_permission")
    op.drop_table("core_user")

    op.execute("DROP TRIGGER trg_core_audit_event_no_delete")
    op.execute("DROP TRIGGER trg_core_audit_event_no_update")
    op.drop_index("ix_core_audit_event_entity", table_name="core_audit_event")
    op.drop_index(op.f("ix_core_audit_event_action"), table_name="core_audit_event")
    op.drop_index(op.f("ix_core_audit_event_occurred_at"), table_name="core_audit_event")
    op.drop_table("core_audit_event")
