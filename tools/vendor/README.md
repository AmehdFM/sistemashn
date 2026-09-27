# Herramienta del vendedor (`vendedor.py`)

CLI interna para generar claves y firmar licencias/recuperación. Nunca se distribuye
con el instalador ni se ejecuta en la máquina del cliente.

## Uso

```
evn\Scripts\python.exe tools\vendor\vendedor.py keygen --out tools\vendor\keys --key-id dev-2026
evn\Scripts\python.exe tools\vendor\vendedor.py sign-license --request SHNREQ1... --business "Repuestos Ejemplo" --key tools\vendor\keys\dev-2026.priv --key-id dev-2026
evn\Scripts\python.exe tools\vendor\vendedor.py sign-recovery --challenge <nonce> --installation-id <uuid> --key tools\vendor\keys\dev-2026.priv --key-id dev-2026
```

`keygen` escribe `<id>.priv` (clave privada PEM, sin cifrar) y `<id>.pub.txt` (clave
pública en base64url) dentro de `--out`, e imprime la clave pública. Rehúsa
sobrescribir si alguno de los dos archivos ya existe.

Tras generar una clave de desarrollo, su valor público (`<id>.pub.txt`) se copia a
`src/sistemashn/core/licensing/keys.py` (`VENDOR_PUBLIC_KEYS`) para que la aplicación
pueda verificar licencias firmadas con ella.

## Seguridad

- La carpeta `keys/` (o cualquier carpeta usada con `--out`) **nunca** se sube a git
  ni se incluye en el instalador del cliente. Está en `.gitignore`.
- Respalda la clave privada (`<id>.priv`) fuera de este repositorio, en un lugar
  seguro y con copia de respaldo: si se pierde, no se pueden firmar más licencias
  con ese `key_id`, y si se filtra, cualquiera puede firmar licencias válidas.
