# ADR-004: notas de API de Flet 1.0 (referencia para UI)

Fecha: 2026-09-27 · Estado: vigente. Verificado contra `evn\Lib\site-packages\flet` 1.0.0.

- Entrada: `ft.run(main)`; eventos tipados `ft.Event[Control]`.
- No existe `ft.ElevatedButton`. Usar `ft.Button`, `ft.FilledButton` (primario), `ft.FilledTonalButton`,
  `ft.OutlinedButton` (secundario), `ft.TextButton`. El texto va en `content=` (str o control), no `text=`.
- `ft.padding` / `ft.border` / `ft.border_radius` ya no son módulos de funciones: usar clases
  `ft.Padding.all(n)|symmetric(...)|only(...)`, `ft.Border.all(w, color)`, `ft.BorderRadius.all(n)`.
- `ft.Alignment.CENTER` (ClassVar); `ft.Colors`, `ft.Icons`.
- Ventana: `page.window.min_width`, `page.window.min_height` (objeto `Window`).
- Tema: `ft.Theme(color_scheme_seed=..., color_scheme=ft.ColorScheme(primary=...))`; no hay `primary=`.
- `DataTable/DataColumn/DataRow/DataCell` y `TextField(password, can_reveal_password, autofocus, label, on_submit)`
  sin cambios relevantes.
- Widgets comunes del proyecto en `sistemashn.core.ui.widgets` (page_header, empty_state, error_banner,
  loading, confirm_dialog, paginated_table, form_field, primary_button, secondary_button, money_text).
  Toda pantalla nueva debe usarlos y el tema de `sistemashn.core.ui.theme`.
