"""Prueba extremo a extremo de `tools/vendor/vendedor.py` vía subprocess (T1.4)."""

import subprocess
import sys
from pathlib import Path

from sistemashn.core.licensing.codec import b64url_decode
from sistemashn.core.licensing.license import build_request_code, verify_license

VENDEDOR = Path(__file__).resolve().parents[2] / "tools" / "vendor" / "vendedor.py"

INSTALLATION_ID = "11111111-1111-1111-1111-111111111111"
VERTICAL = "repuestos"
FINGERPRINT = "f" * 64


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VENDEDOR), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_keygen_sign_license_y_verify_ok(tmp_path) -> None:
    keys_dir = tmp_path / "keys"

    keygen = _run("keygen", "--out", str(keys_dir), "--key-id", "dev-1")
    assert keygen.returncode == 0, keygen.stderr
    clave_publica_b64 = keygen.stdout.strip()
    assert (keys_dir / "dev-1.priv").exists()
    assert (keys_dir / "dev-1.pub.txt").read_text(encoding="utf-8").strip() == clave_publica_b64
    clave_publica_raw = b64url_decode(clave_publica_b64)
    assert len(clave_publica_raw) == 32

    request = build_request_code(INSTALLATION_ID, VERTICAL, FINGERPRINT, "0.1.0")

    sign_license = _run(
        "sign-license",
        "--request",
        request,
        "--business",
        "Repuestos Ejemplo",
        "--key",
        str(keys_dir / "dev-1.priv"),
        "--key-id",
        "dev-1",
    )
    assert sign_license.returncode == 0, sign_license.stderr
    licencia = sign_license.stdout.strip()
    assert licencia.startswith("SHN1.")

    info = verify_license(
        licencia,
        expected_vertical=VERTICAL,
        installation_id=INSTALLATION_ID,
        fingerprint=FINGERPRINT,
        public_keys={"dev-1": clave_publica_raw},
    )
    assert info.business_name == "Repuestos Ejemplo"
    assert info.vertical == VERTICAL


def test_sign_license_con_license_id_explicito(tmp_path) -> None:
    keys_dir = tmp_path / "keys"
    keygen = _run("keygen", "--out", str(keys_dir), "--key-id", "dev-1")
    clave_publica_raw = b64url_decode(keygen.stdout.strip())
    request = build_request_code(INSTALLATION_ID, VERTICAL, FINGERPRINT, "0.1.0")

    sign_license = _run(
        "sign-license",
        "--request",
        request,
        "--business",
        "Otro",
        "--key",
        str(keys_dir / "dev-1.priv"),
        "--key-id",
        "dev-1",
        "--license-id",
        "lic-manual",
    )
    assert sign_license.returncode == 0, sign_license.stderr
    info = verify_license(
        sign_license.stdout.strip(),
        expected_vertical=VERTICAL,
        installation_id=INSTALLATION_ID,
        fingerprint=FINGERPRINT,
        public_keys={"dev-1": clave_publica_raw},
    )
    assert info.license_id == "lic-manual"


def test_sign_recovery_produce_token_valido(tmp_path) -> None:
    keys_dir = tmp_path / "keys"
    keygen = _run("keygen", "--out", str(keys_dir), "--key-id", "dev-1")
    clave_publica_raw = b64url_decode(keygen.stdout.strip())

    sign_recovery = _run(
        "sign-recovery",
        "--challenge",
        "nonce-123",
        "--installation-id",
        INSTALLATION_ID,
        "--key",
        str(keys_dir / "dev-1.priv"),
        "--key-id",
        "dev-1",
    )
    assert sign_recovery.returncode == 0, sign_recovery.stderr
    token = sign_recovery.stdout.strip()
    assert token.startswith("SHNREC1.")

    from sistemashn.core.licensing.codec import verify_signed

    payload = verify_signed(token, "SHNREC1", {"dev-1": clave_publica_raw})
    assert payload == {
        "challenge_nonce": "nonce-123",
        "installation_id": INSTALLATION_ID,
        "action": "reset_admin",
        "key_id": "dev-1",
    }


def test_keygen_rehusa_sobrescribir(tmp_path) -> None:
    keys_dir = tmp_path / "keys"
    primero = _run("keygen", "--out", str(keys_dir), "--key-id", "dev-1")
    assert primero.returncode == 0, primero.stderr

    segundo = _run("keygen", "--out", str(keys_dir), "--key-id", "dev-1")
    assert segundo.returncode != 0
    assert "existe" in segundo.stderr
