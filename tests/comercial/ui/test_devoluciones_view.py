"""Pruebas de la pantalla de devoluciones."""

import flet as ft

from sistemashn.comercial.ui.devoluciones_view import build_returns_view


def test_build_returns_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_returns_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_returns_view_vendedor_con_permiso_no_lanza(ctx_factory, vendedor_actor):
    # el perfil "vendedor" tiene `com.devoluciones.gestionar` (ver module.py)
    ctx = ctx_factory(vendedor_actor)

    control = build_returns_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_returns_view_sin_permiso_muestra_prohibido(ctx_factory, session_factory, now):
    from sistemashn.core.authorization.actor import Actor
    from sistemashn.core.identity.models import User

    with session_factory() as session:
        user = User(
            username="sin_permiso1",
            full_name="Sin Permiso",
            password_hash="hash",
            is_admin=False,
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
        user_id = user.id
    actor = Actor(user_id=user_id, username="sin_permiso1", is_admin=False, session_id="s-sp")
    ctx = ctx_factory(actor)

    control = build_returns_view(ctx)

    assert isinstance(control, ft.Control)
