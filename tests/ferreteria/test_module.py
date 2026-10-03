"""Registro y composición de la vertical Ferretería."""

from sistemashn.app.bootstrap import build_context
from sistemashn.comercial.catalogo.schemas import ProductInput, UnitInput
from sistemashn.comercial.ui.compras_view import build_new_purchase_view
from sistemashn.comercial.ui.cotizaciones_view import build_quotes_view
from sistemashn.comercial.ui.extensions import PRODUCT_FORM_EXTENSIONS_KEY
from sistemashn.comercial.ui.pos_view import build_pos_view
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.identity.models import User
from sistemashn.ferreteria.module import FERRETERIA_MODULE
from sistemashn.ferreteria.ui.screens import FERRETERIA_SCREEN_BUILDERS


def test_modulo_registra_permiso_perfiles_y_pantalla() -> None:
    assert {p.code for p in FERRETERIA_MODULE.permissions} == {"fer.catalogo.gestionar"}
    assert {p.code for p in FERRETERIA_MODULE.profiles} == {
        "ferreteria_gerente",
        "ferreteria_bodega",
    }
    routes = {screen.route for screen in FERRETERIA_MODULE.screens}
    assert routes == FERRETERIA_SCREEN_BUILDERS.keys()


def test_bootstrap_ferreteria_registra_solo_su_vertical(tmp_path) -> None:
    ctx = build_context(tmp_path / "ferreteria", vertical="ferreteria")
    assert ctx.registry.module_codes() == {"core", "comercial", "ferreteria"}
    assert "fer_catalog" in ctx.services
    assert "parts" not in ctx.services
    assert "vehicles" not in ctx.services
    assert len(ctx.services[PRODUCT_FORM_EXTENSIONS_KEY]) == 1


def test_pantallas_operativas_se_construyen_con_servicios_de_ferreteria(tmp_path) -> None:
    ctx = build_context(tmp_path / "ferreteria-ui", vertical="ferreteria")
    now = ctx.clock()
    with ctx.session_factory() as session:
        user = User(
            username="fer_ui",
            full_name="Ferretería UI",
            password_hash="hash",
            is_admin=True,
            is_active=True,
            profile_code=None,
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        ctx.actor = Actor(user_id=user.id, username=user.username, is_admin=True, session_id="ui")

    assert all(builder(ctx) is not None for builder in FERRETERIA_SCREEN_BUILDERS.values())
    assert build_pos_view(ctx) is not None
    assert build_new_purchase_view(ctx) is not None
    assert build_quotes_view(ctx) is not None
    catalog = ctx.service("catalog")
    unit_id = catalog.create_unit(
        ctx.actor, UnitInput(code="UND", name="Unidad", allows_fraction=False)
    )
    product_id = catalog.create_product(
        ctx.actor,
        ProductInput(
            code="FER-UI",
            name="Artículo de prueba",
            unit_id=unit_id,
            tax_rate="0",
            sale_price="1",
            min_stock="0",
        ),
    )
    extension = ctx.services[PRODUCT_FORM_EXTENSIONS_KEY][0]
    assert extension.build(ctx, product_id) is not None
