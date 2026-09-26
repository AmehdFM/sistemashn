"""Interfaz mínima para comprobar el stack de escritorio."""

from __future__ import annotations

import os
from pathlib import Path

import flet as ft


def data_directory() -> Path:
    """Obtiene la ruta de datos externa al directorio instalado."""
    configured = os.environ.get("SISTEMASHN_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    return (Path(local_app_data) if local_app_data else Path.home()) / "SistemasHN"


def build_probe_view(version: str) -> ft.Control:
    status = ft.Text("Pendiente")

    def activate(_event: object) -> None:
        status.value = "Activado"

    return ft.Column(
        controls=[
            ft.Text(f"SistemasHN {version}"),
            ft.Button(content="Activar sonda", on_click=activate),
            status,
        ],
        tight=True,
    )


def main(page: ft.Page) -> None:
    page.title = "SistemasHN"
    page.add(build_probe_view("0.1"), ft.Text(f"Directorio de datos: {data_directory()}"))
