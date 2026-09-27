"""Pruebas de la pantalla de licencia: sin instalación, con instalación y sin licencia."""

import flet as ft

from sistemashn.core.setup.models import Installation
from sistemashn.core.ui.views.license_view import build_license_view


def test_build_license_view_sin_instalacion_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_license_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_license_view_con_instalacion_sin_licencia_no_lanza(
    ctx_factory, admin_actor, session_factory, now
):
    with session_factory() as session:
        session.add(
            Installation(
                id=1,
                installation_id="instalacion-test",
                vertical="repuestos",
                setup_step="done",
                created_at=now,
                completed_at=now,
            )
        )
        session.commit()

    ctx = ctx_factory(admin_actor)

    control = build_license_view(ctx)

    assert isinstance(control, ft.Control)
