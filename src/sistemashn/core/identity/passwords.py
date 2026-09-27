"""Hash y verificación de contraseñas (argon2) y política mínima (T1.2)."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

from sistemashn.core.errors import ValidationError

MIN_LENGTH = 8

_hasher = PasswordHasher()


def validate_password_policy(password: str) -> None:
    """Valida la política mínima de contraseñas. Lanza `ValidationError` si no cumple."""
    if len(password) < MIN_LENGTH:
        raise ValidationError(f"la contraseña debe tener al menos {MIN_LENGTH} caracteres")


def hash_password(password: str) -> str:
    """Valida la política y devuelve el hash argon2 de `password`."""
    validate_password_policy(password)
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Compara `password` contra `password_hash`; nunca lanza si simplemente no coincide."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError, VerificationError, InvalidHash:
        return False


def needs_rehash(password_hash: str) -> bool:
    """True si `password_hash` fue creado con parámetros más débiles que los actuales."""
    return _hasher.check_needs_rehash(password_hash)
