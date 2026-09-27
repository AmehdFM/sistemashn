"""Pruebas de AppContext.service: acceso por nombre y error claro si falta."""

from __future__ import annotations

import pytest

from sistemashn.core.ui.app_context import AppContext


def test_service_devuelve_el_servicio_registrado(session_factory):
    marcador = object()
    ctx = AppContext(
        session_factory=session_factory,
        registry=object(),
        authorizer=object(),
        services={"identity": marcador},
    )
    assert ctx.service("identity") is marcador


def test_service_lanza_keyerror_claro_si_falta(session_factory):
    ctx = AppContext(session_factory=session_factory, registry=object(), authorizer=object())
    with pytest.raises(KeyError, match="identity"):
        ctx.service("identity")
