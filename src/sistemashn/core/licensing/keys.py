"""Claves públicas del vendedor (Ed25519, 32 bytes raw) por id de clave.

Verifican licencias, tokens de recuperación y paquetes de actualización. Las privadas viven solo
en la máquina del vendedor (`tools/vendor/keys/`, fuera de git) y nunca se distribuyen.
`dev-2026` es la clave de desarrollo; antes de entregar a clientes se genera una clave de
producción, se agrega aquí y se retira la de desarrollo.
"""

from sistemashn.core.licensing.codec import b64url_decode

VENDOR_PUBLIC_KEYS: dict[str, bytes] = {
    "dev-2026": b64url_decode("KX3Frksb0PSCjMFL2tyPXptUX8RHkf74JOpfFe1Femk"),
}
