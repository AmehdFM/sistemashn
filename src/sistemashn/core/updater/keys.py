"""Claves públicas para verificar paquetes de actualización firmados (Ed25519, T6.2).

Familia de claves separada de `core/licensing/keys.py`: una fuga o rotación de la
clave de licencias no debe afectar la verificación de paquetes de actualización, y
viceversa. La privada correspondiente a `update-2026` vive solo en la máquina del
vendedor (`tools/vendor/keys/`, fuera de git) y nunca se distribuye; antes de entregar
a clientes se genera una clave de producción, se agrega aquí y se retira la de
desarrollo.
"""

from sistemashn.core.licensing.codec import b64url_decode

UPDATE_PUBLIC_KEYS: dict[str, bytes] = {
    "update-2026": b64url_decode("Gf76f1nHJq3dDmGbgvoBpSAQUgcbJ097lYo4nv9x-PM"),
}
