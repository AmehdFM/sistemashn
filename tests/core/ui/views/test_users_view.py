"""Pruebas de la pantalla de usuarios: construcción, permisos visibles y overrides."""

import flet as ft
from tests.core.ui.views.conftest import contiene_texto

from sistemashn.core.ui.views.users_view import build_users_view, compute_overrides


def test_compute_overrides_otorga_y_revoca():
    perfil = {"core.usuarios.ver", "core.auditoria.ver"}
    seleccionados = {"core.usuarios.ver", "core.ajustes.gestionar"}

    overrides = compute_overrides(perfil, seleccionados)

    assert overrides == {"core.ajustes.gestionar": True, "core.auditoria.ver": False}


def test_compute_overrides_sin_cambios_es_vacio():
    perfil = {"core.usuarios.ver"}

    assert compute_overrides(perfil, perfil) == {}


def test_build_users_view_con_actor_admin_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_users_view(ctx)

    assert isinstance(control, ft.Control)
    assert contiene_texto(control, "admin")
    assert contiene_texto(control, "Nuevo usuario")


def test_actor_sin_permiso_no_ve_boton_nuevo_usuario(ctx_factory, limited_actor):
    ctx = ctx_factory(limited_actor)

    control = build_users_view(ctx)

    assert isinstance(control, ft.Control)
    assert not contiene_texto(control, "Nuevo usuario")
