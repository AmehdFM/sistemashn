from __future__ import annotations

import flet as ft

from sistemashn.probe.app import build_probe_view, main


def test_probe_view_shows_version_and_responds_to_click() -> None:
    view = build_probe_view("0.1")

    assert isinstance(view, ft.Column)
    title, button, status = view.controls
    assert isinstance(title, ft.Text)
    assert title.value == "SistemasHN 0.1"
    assert isinstance(button, ft.Button)
    assert isinstance(status, ft.Text)
    assert status.value == "Pendiente"
    assert button.on_click is not None

    button.on_click(None)

    assert status.value == "Activado"


def test_main_uses_external_data_directory_with_unicode_path(monkeypatch) -> None:
    data_dir = "/tmp/Negocio José/datos de prueba"
    monkeypatch.setenv("SISTEMASHN_DATA_DIR", data_dir)

    class PageProbe:
        title = ""
        controls: list[ft.Control] = []

        def add(self, *controls: ft.Control) -> None:
            self.controls.extend(controls)

    page = PageProbe()
    main(page)

    assert page.title == "SistemasHN"
    assert isinstance(page.controls[0], ft.Column)
    assert isinstance(page.controls[1], ft.Text)
    assert data_dir in page.controls[1].value
