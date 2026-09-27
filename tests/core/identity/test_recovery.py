"""Pruebas de RecoveryService: códigos de recuperación y autorización de vendedor (T1.2)."""

from datetime import timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from sistemashn.core.authorization.actor import SYSTEM_ACTOR, Actor
from sistemashn.core.errors import AuthenticationError, PermissionDenied
from sistemashn.core.identity.passwords import verify_password
from sistemashn.core.identity.recovery import RecoveryService
from sistemashn.core.licensing.codec import sign

CLAVE = "clave1234"
INSTALLATION_ID = "instalacion-1"
KEY_ID = "dev-1"


def _public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


@pytest.fixture
def keypair():
    priv = Ed25519PrivateKey.generate()
    return priv, {KEY_ID: _public_bytes(priv)}


@pytest.fixture
def recovery_service(session_factory, mutable_clock, keypair):
    _, public_keys = keypair
    return RecoveryService(
        session_factory,
        mutable_clock,
        public_keys,
        installation_id_fn=lambda: INSTALLATION_ID,
    )


def _actor(user_id: int, username: str = "u", is_admin: bool = False) -> Actor:
    return Actor(user_id=user_id, username=username, is_admin=is_admin, session_id="s1")


def _token(priv, **overrides) -> str:
    payload = {
        "key_id": KEY_ID,
        "action": "reset_admin",
        "installation_id": INSTALLATION_ID,
        "challenge_nonce": "nonce-1",
    }
    payload.update(overrides)
    return sign(priv, "SHNREC1", payload)


# --- códigos de recuperación --------------------------------------------------------


def test_regenerate_codes_genera_n_codigos_unicos_con_formato(identity_service, recovery_service):
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    codigos = recovery_service.regenerate_codes(SYSTEM_ACTOR, n=8)
    assert len(codigos) == 8
    assert len(set(codigos)) == 8
    for codigo in codigos:
        partes = codigo.split("-")
        assert len(partes) == 3
        assert all(len(p) == 4 for p in partes)


def test_regenerate_codes_requiere_admin(identity_service, recovery_service):
    empleado_id = identity_service.create_user(SYSTEM_ACTOR, "empleado", "Empleado", CLAVE)
    with pytest.raises(PermissionDenied):
        recovery_service.regenerate_codes(_actor(empleado_id, "empleado"))


def test_regenerate_codes_invalida_los_codigos_anteriores(identity_service, recovery_service):
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    primeros = recovery_service.regenerate_codes(SYSTEM_ACTOR, n=8)
    recovery_service.regenerate_codes(SYSTEM_ACTOR, n=8)
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_code(primeros[0], "nuevaClave1")


def test_recover_with_code_restablece_al_admin_activo_mas_antiguo(
    identity_service, recovery_service
):
    admin_id = identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    identity_service.create_user(SYSTEM_ACTOR, "admin2", "Admin Dos", CLAVE, is_admin=True)
    codigos = recovery_service.regenerate_codes(SYSTEM_ACTOR, n=8)

    recovery_service.recover_with_code(codigos[0], "nuevaClave1")

    actor = identity_service.login("admin1", "nuevaClave1")
    assert actor.user_id == admin_id


def test_recover_with_code_usado_dos_veces_falla(identity_service, recovery_service):
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    codigos = recovery_service.regenerate_codes(SYSTEM_ACTOR, n=8)
    recovery_service.recover_with_code(codigos[0], "nuevaClave1")
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_code(codigos[0], "otraClave2")


def test_recover_with_code_invalido_falla(identity_service, recovery_service):
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    recovery_service.regenerate_codes(SYSTEM_ACTOR, n=8)
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_code("ZZZZ-ZZZZ-ZZZZ", "nuevaClave1")


# --- autorización de vendedor --------------------------------------------------------


def test_recover_with_vendor_token_valido(
    identity_service, recovery_service, keypair, session_factory
):
    priv, _ = keypair
    admin_id = identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    texto_desafio = recovery_service.create_challenge()
    nonce = texto_desafio.split(".")[-1]

    token = _token(priv, challenge_nonce=nonce)
    recovery_service.recover_with_vendor_token(token, "nuevaClave1")

    actor = identity_service.login("admin1", "nuevaClave1")
    assert actor.user_id == admin_id


def test_recover_with_vendor_token_firmado_con_otra_clave_falla(identity_service, recovery_service):
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    texto_desafio = recovery_service.create_challenge()
    nonce = texto_desafio.split(".")[-1]

    otra_priv = Ed25519PrivateKey.generate()
    token = _token(otra_priv, challenge_nonce=nonce)
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_vendor_token(token, "nuevaClave1")


def test_recover_with_vendor_token_otra_instalacion_falla(
    identity_service, recovery_service, keypair
):
    priv, _ = keypair
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    texto_desafio = recovery_service.create_challenge()
    nonce = texto_desafio.split(".")[-1]

    token = _token(priv, challenge_nonce=nonce, installation_id="otra-instalacion")
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_vendor_token(token, "nuevaClave1")


def test_recover_with_vendor_token_nonce_usado_dos_veces_falla(
    identity_service, recovery_service, keypair
):
    priv, _ = keypair
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    texto_desafio = recovery_service.create_challenge()
    nonce = texto_desafio.split(".")[-1]

    token = _token(priv, challenge_nonce=nonce)
    recovery_service.recover_with_vendor_token(token, "nuevaClave1")
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_vendor_token(token, "otraClave2")


def test_recover_with_vendor_token_vencido_falla(
    identity_service, recovery_service, keypair, mutable_clock
):
    priv, _ = keypair
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    texto_desafio = recovery_service.create_challenge()
    nonce = texto_desafio.split(".")[-1]

    token = _token(priv, challenge_nonce=nonce)
    mutable_clock.advance(timedelta(hours=73))
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_vendor_token(token, "nuevaClave1")


def test_recover_with_vendor_token_accion_incorrecta_falla(
    identity_service, recovery_service, keypair
):
    priv, _ = keypair
    identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    texto_desafio = recovery_service.create_challenge()
    nonce = texto_desafio.split(".")[-1]

    token = _token(priv, challenge_nonce=nonce, action="otra_cosa")
    with pytest.raises(AuthenticationError):
        recovery_service.recover_with_vendor_token(token, "nuevaClave1")


def test_recover_with_vendor_token_no_deja_la_contrasena_en_claro(
    identity_service, recovery_service, keypair, session_factory
):
    """No debe quedar rastro en claro del hash previo ni de la nueva contraseña."""
    priv, _ = keypair
    admin_id = identity_service.create_user(SYSTEM_ACTOR, "admin1", "Admin", CLAVE, is_admin=True)
    texto_desafio = recovery_service.create_challenge()
    nonce = texto_desafio.split(".")[-1]
    token = _token(priv, challenge_nonce=nonce)
    recovery_service.recover_with_vendor_token(token, "nuevaClave1")

    from sistemashn.core.identity.models import User

    with session_factory() as session:
        admin = session.get(User, admin_id)
        assert verify_password(admin.password_hash, "nuevaClave1")
        assert admin.password_hash != "nuevaClave1"
