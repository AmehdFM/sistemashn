"""Pantalla de contrapartes: búsqueda, alta/edición con deduplicación asistida (T3.4)."""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable

import flet as ft

from sistemashn.comercial.contrapartes.errors import PossibleDuplicate
from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind, PartyView
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.ui.components import safe_page, tiene_permiso
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO_GESTIONAR = "com.contrapartes.gestionar"
DEBOUNCE_SEGUNDOS = 0.3
_ROLES = (("", "Todas"), ("supplier", "Proveedores"), ("customer", "Clientes"))


def build_parties_view(ctx: AppContext) -> ft.Control:
    parties: PartyService = ctx.service("parties")
    puede_gestionar = tiene_permiso(ctx, PERMISO_GESTIONAR)

    campo_busqueda = widgets.form_field("Buscar por nombre o RTN")
    campo_rol = ft.Dropdown(
        label="Rol",
        value="",
        options=[ft.DropdownOption(key=v, text=t) for v, t in _ROLES],
    )
    campo_incluir_inactivos = ft.Checkbox(label="Incluir inactivas", value=False)

    estado = {"page": 1, "texto": ""}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)
    _timer_ref: dict[str, threading.Timer | None] = {"t": None}

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _buscar_ahora() -> None:
        estado["texto"] = campo_busqueda.value or ""
        _recargar(1)

    def _on_change(_: ft.Event[ft.TextField]) -> None:
        anterior = _timer_ref["t"]
        if anterior is not None:
            anterior.cancel()
        nuevo = threading.Timer(DEBOUNCE_SEGUNDOS, _buscar_ahora)
        nuevo.daemon = True
        _timer_ref["t"] = nuevo
        nuevo.start()

    campo_busqueda.on_change = _on_change
    campo_rol.on_change = lambda _: _recargar(1)
    campo_incluir_inactivos.on_change = lambda _: _recargar(1)

    def _confirmar_cambio_activo(control: ft.Control, party: PartyView) -> None:
        nuevo_estado = not party.active
        verbo = "activar" if nuevo_estado else "desactivar"

        def _confirmar() -> None:
            with contextlib.suppress(SistemasHNError):
                parties.set_active(ctx.actor, party.id, nuevo_estado)
            _recargar()

        dialog = widgets.confirm_dialog(
            f"¿{verbo.capitalize()} contraparte?",
            f"¿Desea {verbo} '{party.name}'?",
            _confirmar,
            confirm_text=verbo.capitalize(),
        )
        pagina = safe_page(control)
        if pagina is not None:
            pagina.show_dialog(dialog)

    def _acciones_fila(party: PartyView) -> ft.Control:
        botones = [
            ft.IconButton(
                icon=ft.Icons.VISIBILITY,
                tooltip="Ver / editar",
                on_click=lambda e, p=party: _abrir_dialogo(e.control, p.id),
            )
        ]
        if puede_gestionar:
            botones.append(
                ft.IconButton(
                    icon=ft.Icons.BLOCK if party.active else ft.Icons.CHECK_CIRCLE,
                    tooltip="Desactivar" if party.active else "Activar",
                    on_click=lambda e, p=party: _confirmar_cambio_activo(e.control, p),
                )
            )
        return ft.Row(controls=botones, spacing=0)

    def _render() -> list[ft.Control]:
        acciones: list[ft.Control] = []
        if puede_gestionar:
            acciones.append(
                widgets.primary_button(
                    "Nueva contraparte", lambda e: _abrir_dialogo(e.control, None)
                )
            )
        encabezado = widgets.page_header("Contrapartes", actions=acciones)
        filtros = ft.Row(
            controls=[campo_busqueda, campo_rol, campo_incluir_inactivos],
            spacing=theme.SPACING["md"],
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        try:
            pagina = parties.search(
                ctx.actor,
                estado["texto"],
                role=campo_rol.value or None,
                page=estado["page"],
                include_inactive=bool(campo_incluir_inactivos.value),
            )
        except SistemasHNError as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, filtros, widgets.empty_state("No hay contrapartes que coincidan.")]

        columnas = ["Nombre", "RTN", "Teléfono", "Proveedor", "Cliente", "Estado", "Acciones"]
        filas: list[list[ft.Control]] = []
        for party in pagina.items:
            filas.append(
                [
                    ft.Text(party.name),
                    ft.Text(party.rtn or "—"),
                    ft.Text(party.phone or "—"),
                    ft.Text("Sí" if party.is_supplier else "No"),
                    ft.Text("Sí" if party.is_customer else "No"),
                    ft.Text("Activa" if party.active else "Inactiva"),
                    _acciones_fila(party),
                ]
            )

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, filtros, tabla]

    def _abrir_dialogo(control: ft.Control, party_id: int | None) -> None:
        _dialogo_contraparte(ctx, control, party_id, lambda: _recargar())

    root.controls = _render()
    return root


def _dialogo_contraparte(
    ctx: AppContext, control: ft.Control, party_id: int | None, on_saved: Callable[[], None]
) -> None:
    parties: PartyService = ctx.service("parties")
    puede_gestionar = tiene_permiso(ctx, PERMISO_GESTIONAR)

    party: PartyView | None = None
    if party_id is not None:
        try:
            party = parties.get(ctx.actor, party_id)
        except SistemasHNError as exc:
            dialog_err = ft.AlertDialog(
                modal=True, title=ft.Text("Error"), content=widgets.error_banner(str(exc))
            )
            pagina = safe_page(control)
            if pagina is not None:
                pagina.show_dialog(dialog_err)
            return

    campo_nombre = widgets.form_field(
        "Nombre", value=party.name if party else "", autofocus=party is None
    )
    campo_tipo = ft.Dropdown(
        label="Tipo",
        value=party.kind.value if party else PartyKind.PERSONA.value,
        options=[
            ft.DropdownOption(key=PartyKind.PERSONA.value, text="Persona"),
            ft.DropdownOption(key=PartyKind.NEGOCIO.value, text="Negocio"),
        ],
    )
    campo_rtn = widgets.form_field("RTN", value=party.rtn if party and party.rtn else "")
    campo_telefono = widgets.form_field(
        "Teléfono", value=party.phone if party and party.phone else ""
    )
    campo_correo = widgets.form_field("Correo", value=party.email if party and party.email else "")
    campo_direccion = widgets.form_field(
        "Dirección", value=party.address if party and party.address else ""
    )
    campo_proveedor = ft.Checkbox(label="Es proveedor", value=party.is_supplier if party else False)
    campo_cliente = ft.Checkbox(label="Es cliente", value=party.is_customer if party else False)
    campo_notas = widgets.form_field("Notas", value=party.notes if party and party.notes else "")
    error = ft.Text("", color=theme.ERROR)
    aviso_duplicados = ft.Column(spacing=theme.SPACING["xs"])

    campos_formulario: list[ft.Control] = [
        campo_nombre,
        campo_tipo,
        campo_rtn,
        campo_telefono,
        campo_correo,
        campo_direccion,
        campo_proveedor,
        campo_cliente,
        campo_notas,
    ]
    if not puede_gestionar:
        for c in campos_formulario:
            if isinstance(c, ft.TextField | ft.Dropdown | ft.Checkbox):
                c.disabled = True

    dialog = ft.AlertDialog(
        modal=True, title=ft.Text("Contraparte" if party is None else party.name)
    )
    body = ft.Column(controls=[], tight=True, scroll=ft.ScrollMode.AUTO, height=560, width=520)
    dialog.content = ft.Container(content=body, width=520)

    def _cerrar(_: ft.Event[ft.Control] | None = None) -> None:
        dialog.open = False
        dialog.update()

    def _armar_datos() -> PartyInput:
        return PartyInput(
            kind=PartyKind(campo_tipo.value),
            name=campo_nombre.value or "",
            rtn=(campo_rtn.value or "").strip() or None,
            phone=(campo_telefono.value or "").strip() or None,
            email=(campo_correo.value or "").strip() or None,
            address=(campo_direccion.value or "").strip() or None,
            is_supplier=bool(campo_proveedor.value),
            is_customer=bool(campo_cliente.value),
            notes=(campo_notas.value or "").strip() or None,
        )

    def _guardar_forzado(_: ft.Event[ft.Control] | None = None) -> None:
        try:
            data = _armar_datos()
        except Exception as exc:  # errores de validación de Pydantic
            error.value = str(exc)
            error.update()
            return
        try:
            if party is None:
                parties.create(ctx.actor, data, allow_duplicate=True)
            else:
                parties.update(ctx.actor, party.id, data, allow_duplicate=True)
            on_saved()
            _cerrar()
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()

    def _guardar(_: ft.Event[ft.Control]) -> None:
        try:
            data = _armar_datos()
        except Exception as exc:
            error.value = str(exc)
            error.update()
            return

        aviso_duplicados.controls = []
        try:
            if party is None:
                parties.create(ctx.actor, data)
                on_saved()
                _cerrar()
            else:
                parties.update(ctx.actor, party.id, data)
                on_saved()
                _cerrar()
        except PossibleDuplicate as exc:
            error.value = ""
            candidatos = ft.Column(
                controls=[
                    ft.Text(f"- {c.name} (#{c.id}) RTN: {c.rtn or '—'}") for c in exc.candidates
                ]
            )
            aviso_duplicados.controls = [
                widgets.error_banner("Se encontraron posibles contrapartes duplicadas:"),
                candidatos,
                widgets.secondary_button("Crear de todos modos", _guardar_forzado),
            ]
            body.update()
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()

    contenido: list[ft.Control] = [
        ft.Text("Datos generales", weight=ft.FontWeight.BOLD),
        *campos_formulario,
        error,
        aviso_duplicados,
    ]
    if puede_gestionar:
        contenido.append(widgets.primary_button("Guardar", _guardar))

    body.controls = contenido
    dialog.actions = [widgets.secondary_button("Cerrar", _cerrar)]

    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)
