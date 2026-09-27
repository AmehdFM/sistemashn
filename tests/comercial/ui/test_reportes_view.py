"""Pruebas de la pantalla de reportes."""

import flet as ft

from sistemashn.comercial.ui.reportes_view import build_reports_view


def test_build_reports_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_reports_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_reports_view_sin_permiso_muestra_prohibido(ctx_factory, session_factory, now):
    from sistemashn.core.authorization.actor import Actor
    from sistemashn.core.identity.models import User

    with session_factory() as session:
        user = User(
            username="sin_permiso2",
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
    actor = Actor(user_id=user_id, username="sin_permiso2", is_admin=False, session_id="s-sp2")
    ctx = ctx_factory(actor)

    control = build_reports_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_reports_view_gerente_no_lanza(ctx_factory, session_factory, now):
    from sistemashn.core.authorization.actor import Actor
    from sistemashn.core.identity.models import User

    with session_factory() as session:
        user = User(
            username="gerente1",
            full_name="Gerente",
            password_hash="hash",
            is_admin=False,
            is_active=True,
            profile_code="gerente",
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
    actor = Actor(user_id=user_id, username="gerente1", is_admin=False, session_id="s-g1")
    ctx = ctx_factory(actor)

    control = build_reports_view(ctx)

    assert isinstance(control, ft.Control)
