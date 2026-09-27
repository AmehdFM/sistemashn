"""Pruebas de la pantalla de auditoría: construcción con y sin eventos, filtros."""

import flet as ft

from sistemashn.core.ui.views.audit_view import build_audit_view


def test_build_audit_view_sin_eventos_extra_no_lanza(ctx_factory, admin_actor):
    """Solo existe el evento de creación de `admin_actor` en la fixture (o ninguno)."""
    ctx = ctx_factory(admin_actor)

    control = build_audit_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_audit_view_con_eventos_no_lanza(ctx_factory, admin_actor, limited_actor):
    ctx = ctx_factory(admin_actor)
    identity = ctx.service("identity")
    identity.update_user(admin_actor, limited_actor.user_id, full_name="Vendedor Actualizado")

    control = build_audit_view(ctx)

    assert isinstance(control, ft.Control)
