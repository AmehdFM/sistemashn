"""Pruebas de la lógica de decisión de vista y construcción de setup/login (T1.6b-1)."""

from __future__ import annotations

import flet as ft
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from sistemashn.core.audit.service import AuditQueryService
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.identity.recovery import RecoveryService
from sistemashn.core.identity.service import IdentityService
from sistemashn.core.licensing.codec import sign
from sistemashn.core.licensing.license import LICENSE_PREFIX
from sistemashn.core.licensing.service import LicenseService
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE
from sistemashn.core.settings.schemas import BusinessInput
from sistemashn.core.settings.service import SettingsService
from sistemashn.core.setup.service import SetupService
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.app_shell import initial_view_kind
from sistemashn.core.ui.login_view import build_login_view
from sistemashn.core.ui.setup_view import build_setup_view

VERTICAL = "repuestos"
APP_VERSION = "0.1.0"
KEY_ID = "dev-1"
FINGERPRINT = "f" * 64

DATOS_NEGOCIO = BusinessInput(
    name="Repuestos Ejemplo",
    legal_name="Repuestos Ejemplo S. de R.L.",
    rtn="08011999012345",
    address="Col. Centro",
    phone="9999-9999",
    email="ejemplo@correo.com",
)


def _public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


@pytest.fixture
def keypair():
    priv = Ed25519PrivateKey.generate()
    return priv, {KEY_ID: _public_bytes(priv)}


def _license_text(priv, installation_id: str) -> str:
    payload = {
        "license_id": "lic-1",
        "vertical": VERTICAL,
        "business_name": "Repuestos Ejemplo",
        "installation_id": installation_id,
        "fingerprint": FINGERPRINT,
        "edition": "perpetua",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "format": 1,
        "key_id": KEY_ID,
    }
    return sign(priv, LICENSE_PREFIX, payload)


@pytest.fixture
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(CORE_MODULE)
    reg.validate()
    return reg


@pytest.fixture
def license_service(session_factory, keypair, clock) -> LicenseService:
    _, public_keys = keypair
    return LicenseService(
        session_factory, public_keys, fingerprint_fn=lambda: FINGERPRINT, clock=clock
    )


@pytest.fixture
def setup_service(session_factory, clock, license_service, tmp_path) -> SetupService:
    return SetupService(
        session_factory, clock, license_service, tmp_path / "datos", VERTICAL, APP_VERSION
    )


@pytest.fixture
def ctx(session_factory, registry, clock, setup_service, tmp_path) -> AppContext:
    authorizer = Authorizer(registry, clock)
    installation = setup_service.ensure_installation()
    context = AppContext(
        session_factory=session_factory,
        registry=registry,
        authorizer=authorizer,
        clock=clock,
        data_dir=tmp_path / "datos",
    )
    context.services["setup"] = setup_service
    context.services["identity"] = IdentityService(session_factory, authorizer, clock)
    context.services["recovery"] = RecoveryService(
        session_factory, clock, {}, lambda: installation.installation_id
    )
    context.services["settings"] = SettingsService(session_factory, authorizer, clock, tmp_path)
    context.services["audit"] = AuditQueryService(session_factory, authorizer)
    return context


def test_initial_view_kind_es_setup_antes_de_terminar(ctx):
    assert initial_view_kind(ctx) == "setup"


def test_initial_view_kind_es_login_sin_actor_tras_setup(ctx, keypair):
    priv, _ = keypair
    setup_service: SetupService = ctx.services["setup"]
    instalacion = setup_service.ensure_installation()
    setup_service.submit_license(_license_text(priv, instalacion.installation_id))
    setup_service.submit_business(DATOS_NEGOCIO)
    setup_service.create_admin("admin", "Admin Principal", "clave1234")
    setup_service.confirm_recovery_codes_saved()

    assert initial_view_kind(ctx) == "login"


def test_initial_view_kind_es_shell_con_actor(ctx, keypair):
    priv, _ = keypair
    setup_service: SetupService = ctx.services["setup"]
    instalacion = setup_service.ensure_installation()
    setup_service.submit_license(_license_text(priv, instalacion.installation_id))
    setup_service.submit_business(DATOS_NEGOCIO)
    setup_service.create_admin("admin", "Admin Principal", "clave1234")
    setup_service.confirm_recovery_codes_saved()

    ctx.actor = Actor(user_id=1, username="admin", is_admin=True, session_id="s1")
    assert initial_view_kind(ctx) == "shell"


def test_build_setup_view_construye_en_cada_paso_sin_lanzar(ctx, keypair):
    priv, _ = keypair
    setup_service: SetupService = ctx.services["setup"]
    instalacion = setup_service.ensure_installation()

    control = build_setup_view(ctx, on_done=lambda: None)
    assert isinstance(control, ft.Control)

    setup_service.submit_license(_license_text(priv, instalacion.installation_id))
    control = build_setup_view(ctx, on_done=lambda: None)
    assert isinstance(control, ft.Control)

    setup_service.submit_business(DATOS_NEGOCIO)
    control = build_setup_view(ctx, on_done=lambda: None)
    assert isinstance(control, ft.Control)

    setup_service.create_admin("admin", "Admin Principal", "clave1234")
    control = build_setup_view(ctx, on_done=lambda: None)
    assert isinstance(control, ft.Control)

    setup_service.confirm_recovery_codes_saved()
    llamado = {"done": False}
    build_setup_view(ctx, on_done=lambda: llamado.__setitem__("done", True))
    assert llamado["done"] is True


def test_build_login_view_construye_sin_lanzar(ctx, keypair):
    priv, _ = keypair
    setup_service: SetupService = ctx.services["setup"]
    instalacion = setup_service.ensure_installation()
    setup_service.submit_license(_license_text(priv, instalacion.installation_id))
    setup_service.submit_business(DATOS_NEGOCIO)
    setup_service.create_admin("admin", "Admin Principal", "clave1234")
    setup_service.confirm_recovery_codes_saved()

    control = build_login_view(ctx, on_login=lambda actor: None)
    assert isinstance(control, ft.Control)
