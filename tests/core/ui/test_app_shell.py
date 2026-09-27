"""Pruebas del cierre limpio de `DesktopApp` (T6.3: borra `.app.lock` al cerrar)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.app_shell import DesktopApp


@dataclass
class FakeRegistry:
    def screens(self) -> list:
        return []


class FakeAuthorizer:
    def can(self, session, actor, code: str) -> bool:
        return True


@dataclass
class FakeServices:
    data: dict = field(default_factory=dict)


def test_on_close_borra_el_archivo_de_bloqueo_si_existe(session_factory, tmp_path):
    lock = tmp_path / ".app.lock"
    lock.write_text("1234", encoding="utf-8")

    ctx = AppContext(
        session_factory=session_factory,
        registry=FakeRegistry(),
        authorizer=FakeAuthorizer(),
        data_dir=tmp_path,
    )
    app = DesktopApp(ctx, builders={})

    app._on_close()

    assert not lock.exists()


def test_on_close_no_falla_si_no_hay_archivo_de_bloqueo(session_factory, tmp_path):
    ctx = AppContext(
        session_factory=session_factory,
        registry=FakeRegistry(),
        authorizer=FakeAuthorizer(),
        data_dir=tmp_path,
    )
    app = DesktopApp(ctx, builders={})

    app._on_close()
