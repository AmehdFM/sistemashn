"""Pantalla de usuarios: lista, alta, edición, permisos, activar/desactivar y clave (T1.6b-2)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

import flet as ft

from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.identity.service import UserView
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.views import format_local_datetime

_PERMISO_GESTIONAR = "core.usuarios.gestionar"


def compute_overrides(profile_perms: Iterable[str], selected: Iterable[str]) -> dict[str, bool]:
    """Overrides mínimos para que los permisos efectivos pasen a ser `selected`.

    Un código presente en `selected` pero no en `profile_perms` se otorga (`True`);
    uno presente en `profile_perms` pero ausente de `selected` se revoca (`False`).
    """
    base = set(profile_perms)
    elegidos = set(selected)
    overrides: dict[str, bool] = {}
    for code in elegidos - base:
        overrides[code] = True
    for code in base - elegidos:
        overrides[code] = False
    return overrides


def _tiene_permiso(ctx: AppContext, code: str) -> bool:
    if ctx.actor is None:
        return False
    with session_scope(ctx.session_factory, readonly=True) as session:
        return ctx.authorizer.can(session, ctx.actor, code)


def _abrir_dialogo(dialog: ft.AlertDialog, control: ft.Control) -> None:
    if control.page is not None:
        control.page.show_dialog(dialog)


def build_users_view(ctx: AppContext) -> ft.Control:
    identity = ctx.service("identity")
    permissions_service = ctx.service("permissions")

    puede_gestionar = _tiene_permiso(ctx, _PERMISO_GESTIONAR)

    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _perfil_label(profile_code: str | None) -> str:
        if profile_code is None:
            return "—"
        perfil = ctx.registry.profiles().get(profile_code)
        return perfil.label if perfil is not None else profile_code

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _dialogo_nuevo_usuario(control: ft.Control) -> None:
        campo_usuario = widgets.form_field("Usuario", autofocus=True)
        campo_nombre = widgets.form_field("Nombre completo")
        campo_password = widgets.form_field("Contraseña", password=True)
        perfiles = sorted(ctx.registry.profiles().values(), key=lambda p: p.label)
        campo_perfil = ft.Dropdown(
            label="Perfil",
            options=[ft.DropdownOption(key=p.code, text=p.label) for p in perfiles],
        )
        campo_admin = ft.Checkbox(label="Administrador", value=False)
        error = ft.Text("", color=theme.ERROR)

        columna = [campo_usuario, campo_nombre, campo_password, campo_perfil]
        if ctx.actor is not None and ctx.actor.is_admin:
            columna.append(campo_admin)
        columna.append(error)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo usuario"),
            content=ft.Column(controls=columna, tight=True),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            es_admin_solicitado = campo_admin in columna and bool(campo_admin.value)
            try:
                identity.create_user(
                    ctx.actor,
                    campo_usuario.value or "",
                    campo_nombre.value or "",
                    campo_password.value or "",
                    profile_code=campo_perfil.value,
                    is_admin=es_admin_solicitado,
                )
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()
            _recargar(1)

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Crear", _guardar),
        ]
        _abrir_dialogo(dialog, control)

    def _dialogo_editar(control: ft.Control, usuario: UserView) -> None:
        campo_nombre = widgets.form_field("Nombre completo", value=usuario.full_name)
        perfiles = sorted(ctx.registry.profiles().values(), key=lambda p: p.label)
        campo_perfil = ft.Dropdown(
            label="Perfil",
            value=usuario.profile_code,
            options=[ft.DropdownOption(key=p.code, text=p.label) for p in perfiles],
        )
        error = ft.Text("", color=theme.ERROR)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar '{usuario.username}'"),
            content=ft.Column(controls=[campo_nombre, campo_perfil, error], tight=True),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                identity.update_user(
                    ctx.actor,
                    usuario.id,
                    full_name=campo_nombre.value,
                    profile_code=campo_perfil.value,
                )
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()
            _recargar()

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Guardar", _guardar),
        ]
        _abrir_dialogo(dialog, control)

    def _dialogo_permisos(control: ft.Control, usuario: UserView) -> None:
        with session_scope(ctx.session_factory, readonly=True) as session:
            efectivos = ctx.authorizer.effective_permissions(session, usuario.id)

        perfil = ctx.registry.profiles().get(usuario.profile_code) if usuario.profile_code else None
        permisos_perfil = perfil.permissions if perfil is not None else frozenset()

        por_grupo: dict[str, list] = {}
        for definicion in ctx.registry.permissions().values():
            por_grupo.setdefault(definicion.group, []).append(definicion)

        casillas: dict[str, ft.Checkbox] = {}
        grupos: list[ft.Control] = []
        for grupo in sorted(por_grupo):
            controles_grupo: list[ft.Control] = []
            for definicion in sorted(por_grupo[grupo], key=lambda d: d.label):
                casilla = ft.Checkbox(label=definicion.label, value=definicion.code in efectivos)
                casillas[definicion.code] = casilla
                controles_grupo.append(casilla)
            grupos.append(
                ft.Column(
                    controls=[
                        ft.Text(grupo, weight=ft.FontWeight.BOLD),
                        *controles_grupo,
                    ],
                    spacing=theme.SPACING["xs"],
                )
            )

        error = ft.Text("", color=theme.ERROR)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Permisos de '{usuario.username}'"),
            content=ft.Column(
                controls=[*grupos, error], tight=True, scroll=ft.ScrollMode.AUTO, height=400
            ),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            seleccionados = {code for code, casilla in casillas.items() if casilla.value}
            overrides = compute_overrides(permisos_perfil, seleccionados)
            try:
                permissions_service.set_user_permissions(
                    ctx.actor, usuario.id, usuario.profile_code, overrides
                )
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()
            _recargar()

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Guardar", _guardar),
        ]
        _abrir_dialogo(dialog, control)

    def _dialogo_restablecer(control: ft.Control, usuario: UserView) -> None:
        campo_password = widgets.form_field("Nueva contraseña", password=True, autofocus=True)
        error = ft.Text("", color=theme.ERROR)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Restablecer contraseña de '{usuario.username}'"),
            content=ft.Column(controls=[campo_password, error], tight=True),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                identity.reset_password(ctx.actor, usuario.id, campo_password.value or "")
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Restablecer", _guardar),
        ]
        _abrir_dialogo(dialog, control)

    def _confirmar_cambio_activo(control: ft.Control, usuario: UserView) -> None:
        nuevo_estado = not usuario.is_active
        verbo = "activar" if nuevo_estado else "desactivar"

        def _confirmar() -> None:
            identity.set_active(ctx.actor, usuario.id, nuevo_estado)
            _recargar()

        dialog = widgets.confirm_dialog(
            f"¿{verbo.capitalize()} usuario?",
            f"¿Desea {verbo} a '{usuario.username}'?",
            _confirmar,
            confirm_text=verbo.capitalize(),
        )
        _abrir_dialogo(dialog, control)

    def _acciones_fila(usuario: UserView) -> ft.Control:
        return ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.EDIT,
                    tooltip="Editar",
                    on_click=lambda e, u=usuario: _dialogo_editar(e.control, u),
                ),
                ft.IconButton(
                    icon=ft.Icons.SECURITY,
                    tooltip="Permisos",
                    on_click=lambda e, u=usuario: _dialogo_permisos(e.control, u),
                ),
                ft.IconButton(
                    icon=ft.Icons.BLOCK if usuario.is_active else ft.Icons.CHECK_CIRCLE,
                    tooltip="Desactivar" if usuario.is_active else "Activar",
                    on_click=lambda e, u=usuario: _confirmar_cambio_activo(e.control, u),
                ),
                ft.IconButton(
                    icon=ft.Icons.LOCK_RESET,
                    tooltip="Restablecer contraseña",
                    on_click=lambda e, u=usuario: _dialogo_restablecer(e.control, u),
                ),
            ],
            spacing=0,
        )

    def _render() -> list[ft.Control]:
        acciones: list[ft.Control] = []
        if puede_gestionar:
            acciones.append(
                widgets.primary_button("Nuevo usuario", lambda e: _dialogo_nuevo_usuario(e.control))
            )
        encabezado = widgets.page_header("Usuarios", actions=acciones)

        try:
            pagina = identity.list_users(ctx.actor, estado["page"])
        except SistemasHNError as exc:
            return [encabezado, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, widgets.empty_state("No hay usuarios registrados.")]

        columnas = ["Usuario", "Nombre", "Perfil", "Admin", "Activo", "Bloqueado"]
        if puede_gestionar:
            columnas.append("Acciones")

        filas: list[list[ft.Control]] = []
        for usuario in pagina.items:
            celdas: list[ft.Control] = [
                ft.Text(usuario.username),
                ft.Text(usuario.full_name),
                ft.Text(_perfil_label(usuario.profile_code)),
                ft.Text("Sí" if usuario.is_admin else "No"),
                ft.Text("Sí" if usuario.is_active else "No"),
                ft.Text(
                    f"Hasta {format_local_datetime(usuario.locked_until)}"
                    if usuario.locked_until is not None and usuario.locked_until > datetime.now(UTC)
                    else "No"
                ),
            ]
            if puede_gestionar:
                celdas.append(_acciones_fila(usuario))
            filas.append(celdas)

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, tabla]

    root.controls = _render()
    return root
