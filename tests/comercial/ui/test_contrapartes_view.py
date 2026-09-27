"""Pruebas de la pantalla de contrapartes: construcción, permisos y duplicados."""

import flet as ft
from tests.comercial.ui.conftest import contiene_texto

from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.ui.contrapartes_view import build_parties_view


def test_build_parties_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_parties_view(ctx)

    assert isinstance(control, ft.Control)
    assert contiene_texto(control, "Nueva contraparte")


def test_vendedor_no_ve_boton_nueva_contraparte(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_parties_view(ctx)

    assert isinstance(control, ft.Control)
    assert not contiene_texto(control, "Nueva contraparte")


def test_build_parties_view_con_contraparte(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)
    parties: PartyService = ctx.service("parties")
    parties.create(
        admin_actor,
        PartyInput(kind=PartyKind.NEGOCIO, name="Repuestos El Sol", is_supplier=True),
    )

    control = build_parties_view(ctx)

    assert isinstance(control, ft.Control)
    assert contiene_texto(control, "Repuestos El Sol")


def test_deteccion_de_duplicados_no_lanza(ctx_factory, admin_actor):
    from sistemashn.comercial.contrapartes.errors import PossibleDuplicate
    from sistemashn.core.db.session import session_scope

    ctx = ctx_factory(admin_actor)
    parties: PartyService = ctx.service("parties")
    parties.create(admin_actor, PartyInput(kind=PartyKind.PERSONA, name="Juan Pérez"))

    with session_scope(ctx.session_factory, readonly=True) as session:
        candidatos = parties.find_duplicates(session, "Juan Pérez", None)
    assert len(candidatos) == 1
    assert candidatos[0].name == "Juan Pérez"

    try:
        parties.create(admin_actor, PartyInput(kind=PartyKind.PERSONA, name="Juan Pérez"))
    except PossibleDuplicate as exc:
        assert exc.candidates[0].name == "Juan Pérez"
    else:
        raise AssertionError("se esperaba PossibleDuplicate")
