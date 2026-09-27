"""Herramienta de línea de comandos del vendedor: claves, licencias y recuperación (T1.4).

Uso exclusivo del vendedor; nunca se distribuye con el instalador ni se ejecuta en la
máquina del cliente. Solo importa de `sistemashn.core.licensing.codec`/`license`, nunca
al revés. Ver `tools/vendor/README.md`.
"""

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
)

from sistemashn.core.licensing import codec
from sistemashn.core.licensing.license import (
    LICENSE_PREFIX,
    LicenseError,
    parse_request_code,
)
from sistemashn.core.updater.package import manifest_signing_bytes

RECOVERY_PREFIX = "SHNREC1"


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    clave = load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(clave, Ed25519PrivateKey):
        raise SystemExit(f"la clave en {path} no es Ed25519")
    return clave


def cmd_keygen(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    priv_path = out_dir / f"{args.key_id}.priv"
    pub_path = out_dir / f"{args.key_id}.pub.txt"
    if priv_path.exists() or pub_path.exists():
        existente = priv_path if priv_path.exists() else pub_path
        print(f"error: ya existe {existente}, no se sobrescribe", file=sys.stderr)
        return 1

    clave_privada = Ed25519PrivateKey.generate()
    priv_pem = clave_privada.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    priv_path.write_bytes(priv_pem)

    clave_publica_raw = clave_privada.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    clave_publica_b64 = codec.b64url_encode(clave_publica_raw)
    pub_path.write_text(clave_publica_b64, encoding="utf-8")

    print(clave_publica_b64)
    return 0


def cmd_sign_license(args: argparse.Namespace) -> int:
    solicitud = parse_request_code(args.request)
    clave_privada = _load_private_key(Path(args.key))

    payload = {
        "license_id": args.license_id or uuid.uuid4().hex,
        "vertical": solicitud["vertical"],
        "business_name": args.business,
        "installation_id": solicitud["installation_id"],
        "fingerprint": solicitud["fingerprint"],
        "edition": "perpetua",
        "issued_at": datetime.now(UTC).isoformat(),
        "format": 1,
        "key_id": args.key_id,
    }
    print(codec.sign(clave_privada, LICENSE_PREFIX, payload))
    return 0


def cmd_sign_recovery(args: argparse.Namespace) -> int:
    clave_privada = _load_private_key(Path(args.key))
    payload = {
        "challenge_nonce": args.challenge,
        "installation_id": args.installation_id,
        "action": "reset_admin",
        "key_id": args.key_id,
    }
    print(codec.sign(clave_privada, RECOVERY_PREFIX, payload))
    return 0


def cmd_sign_update(args: argparse.Namespace) -> int:
    clave_privada = _load_private_key(Path(args.key))
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest["key_id"] = args.key_id
    firma = clave_privada.sign(manifest_signing_bytes(manifest))
    manifest["signature"] = codec.b64url_encode(firma)

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"manifest firmado: {manifest_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vendedor", description="Herramienta del vendedor SistemasHN"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_keygen = sub.add_parser("keygen", help="genera un par de claves Ed25519")
    p_keygen.add_argument("--out", required=True, help="carpeta donde escribir las claves")
    p_keygen.add_argument("--key-id", required=True, help="identificador de la clave")
    p_keygen.set_defaults(func=cmd_keygen)

    p_sign_license = sub.add_parser(
        "sign-license", help="firma una licencia a partir de un código de solicitud"
    )
    p_sign_license.add_argument("--request", required=True, help="código SHNREQ1... del cliente")
    p_sign_license.add_argument("--business", required=True, help="nombre del negocio")
    p_sign_license.add_argument("--key", required=True, help="ruta al .priv del vendedor")
    p_sign_license.add_argument("--key-id", required=True, help="id de la clave usada")
    p_sign_license.add_argument("--license-id", help="id de licencia; por defecto se genera uno")
    p_sign_license.set_defaults(func=cmd_sign_license)

    p_sign_recovery = sub.add_parser(
        "sign-recovery", help="firma un token de recuperación de administrador"
    )
    p_sign_recovery.add_argument("--challenge", required=True, help="nonce del desafío (texto)")
    p_sign_recovery.add_argument("--installation-id", required=True, help="id de la instalación")
    p_sign_recovery.add_argument("--key", required=True, help="ruta al .priv del vendedor")
    p_sign_recovery.add_argument("--key-id", required=True, help="id de la clave usada")
    p_sign_recovery.set_defaults(func=cmd_sign_recovery)

    p_sign_update = sub.add_parser(
        "sign-update", help="firma el manifest.json de un paquete de actualización"
    )
    p_sign_update.add_argument("--manifest", required=True, help="ruta al manifest.json a firmar")
    p_sign_update.add_argument("--key", required=True, help="ruta al .priv del vendedor")
    p_sign_update.add_argument("--key-id", required=True, help="id de la clave usada")
    p_sign_update.set_defaults(func=cmd_sign_update)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except LicenseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
