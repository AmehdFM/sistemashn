"""Pruebas de hash, verificación y política de contraseñas (T1.2)."""

import pytest

from sistemashn.core.errors import ValidationError
from sistemashn.core.identity.passwords import (
    hash_password,
    needs_rehash,
    validate_password_policy,
    verify_password,
)


def test_hash_nunca_es_igual_a_la_contrasena_y_verify_reconoce_correcta_e_incorrecta() -> None:
    hash_ = hash_password("clave1234")
    assert hash_ != "clave1234"
    assert "clave1234" not in hash_
    assert verify_password(hash_, "clave1234") is True
    assert verify_password(hash_, "otra-clave") is False


def test_verify_password_con_hash_invalido_no_lanza() -> None:
    assert verify_password("no-es-un-hash-argon2", "cualquier") is False


def test_politica_minimo_8_caracteres() -> None:
    validate_password_policy("12345678")
    with pytest.raises(ValidationError):
        validate_password_policy("1234567")


def test_hash_password_aplica_la_politica() -> None:
    with pytest.raises(ValidationError):
        hash_password("corta")


def test_needs_rehash_falso_para_un_hash_recien_creado() -> None:
    hash_ = hash_password("clave1234")
    assert needs_rehash(hash_) is False
