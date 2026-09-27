# ADR-003: contrato de actualización local de ensayo y recuperación (Etapa 0)

Fecha: 2026-09-26 · Estado: aceptada

## Contexto

Fase 6 traerá el actualizador real (proceso externo, firma de paquetes, reintentos
tras reinicio). En Etapa 0 solo se valida el **contrato** de datos y el **procedimiento**
de aplicar/revertir una actualización sobre una instalación y una base de prueba, en
memoria de proceso, sin actualizador externo. Implementado en
`src/sistemashn/core/operations/probe_update.py`, reutilizando sin modificar
`create_backup`/`verify_backup` (`operations/backup.py`), `restore_to_trial`
(`operations/restore.py`) y `migrate.upgrade`/`migrate.current_revision`
(`core/db/migrate.py`).

## Formato del paquete

Un ZIP con `manifest.json` en la raíz y los archivos del programa bajo
`payload/<ruta>`:

```json
{
  "format": 1,
  "version": "0.2.0",
  "min_from_version": "0.1.0",
  "schema_revision": "0002",
  "files": {
    "app/main.exe": "<sha256 hex>",
    "app/data/plantilla.pdf": "<sha256 hex>"
  }
}
```

- `format`: versión del formato de manifest (hoy solo `1`).
- `version` / `min_from_version`: cadenas `N.N.N...`, comparadas como tuplas de
  enteros (nunca como texto: `"0.10.0" > "0.9.0"`).
- `schema_revision`: revisión de Alembic destino (`migrate.upgrade` la aplica tal cual).
- `files`: claves con `/` como separador, relativas a la raíz de la instalación;
  cada valor es el sha256 hexadecimal del contenido esperado.

Una instalación es una carpeta con los archivos del programa y un archivo `VERSION`
(texto plano, p. ej. `0.1.0`) en su raíz.

## Validación (`validate_package`, antes de tocar disco)

Se rechaza el paquete completo (`InvalidPackageError`, subclase de `OperationError`,
definida en `probe_update.py`) si:

- el ZIP no se puede abrir, o `manifest.json` está ausente/no es JSON válido/no es
  un objeto con los campos requeridos;
- `format` no es `1`;
- alguna ruta en `files` es absoluta, contiene `..`, usa `\`, o empieza con letra de
  unidad (`C:`) — se comprueba antes de tocar el ZIP de payload;
- falta en `payload/` algún archivo listado en el manifest, o sobra alguno no listado;
- el sha256 de algún archivo de `payload/` no coincide con el declarado;
- `version` del paquete es `<=` la versión instalada (anti-downgrade, incluye
  igualdad);
- la versión instalada es `<` `min_from_version` (el paquete no sabe migrar desde
  una versión tan vieja).

Todas estas comprobaciones ocurren antes de extraer nada o tocar la instalación o la
base; si fallan, no se crea ningún directorio de trabajo ni se escribe el log.

## Procedimiento de aplicación (`apply_probe_update`)

1. `validate_package`.
2. Extrae el payload a `work_dir/staging-<timestamp>/`.
3. Respalda: copia completa de la instalación a
   `work_dir/rollback-<timestamp>/app/`, y `create_backup` de la base a
   `work_dir/rollback-<timestamp>/db.sqlite`. Este respaldo se hace **antes** de
   modificar nada, para poder revertir sin depender de que la fuente sobreviva.
4. Reemplaza cada archivo listado en la instalación: se copia a un temporal en el
   mismo directorio y se reemplaza con `os.replace` (atómico dentro del mismo
   volumen); al final se reescribe `VERSION` con la nueva versión, también por
   temporal + `os.replace`.
5. `migrate.upgrade(db, schema_revision)`.
6. Si se pasó `startup_check(installation, db_path)`, se invoca; cualquier
   excepción se trata como fallo.
7. Se verifica que `migrate.current_revision(db) == schema_revision` y que
   `verify_backup(db).ok` sea verdadero.

Si cualquier paso de 4 a 7 falla (excepción propagada, incluida la de un
`startup_check` o un `schema_revision` inexistente), se revierte:

- se eliminan `db_path-wal`/`db_path-shm` residuales (por si la migración o la app
  dejaron un WAL abierto) antes de tocar la base;
- se borra la carpeta de instalación completa y se restituye desde
  `rollback-<timestamp>/app/` (no se conserva nada escrito durante el intento
  fallido, incluidos archivos nuevos no contemplados por el manifest);
- se restaura la base con `restore_to_trial(rollback_db, db_path, overwrite=True)`.

En ambos casos (éxito o fallo) se añade una línea JSON a
`work_dir/update-log.jsonl` con fecha UTC, `from_version`, `to_version`, `ok`,
`rolled_back` y `error`. Un `InvalidPackageError` de validación (paso 1) se
relanza tal cual, sin crear directorios de trabajo ni escribir el log: no se llegó
a tocar nada.

## Supuestos y límites de esta etapa

- **Sin proceso externo**: todo ocurre en el mismo proceso que invoca
  `apply_probe_update`. El actualizador real de Fase 6 será un ejecutable aparte
  que espera a que la aplicación cierre, aplica el paquete y puede reintentar tras
  un reinicio; ese flujo no está cubierto aquí.
- **Ningún proceso tiene la base abierta**: se asume acceso exclusivo a `db_path`
  durante todo el procedimiento. No hay bloqueo ni verificación de que otro proceso
  (la app en ejecución) no la esté usando; eso es responsabilidad del actualizador
  real, que debe esperar el cierre de la aplicación antes de llamar a esta función.
- **Sin firma ni verificación de origen**: el paquete solo se valida por estructura,
  rutas y hashes declarados por el propio manifest — nada garantiza que el manifest
  no haya sido alterado junto con el ZIP. La firma criptográfica del paquete queda
  fuera de alcance de Etapa 0.
- **Sin operaciones de sistema de archivos transaccionales**: el reemplazo de
  archivos es "mejor esfuerzo" (temporal + `os.replace` por archivo, no todo el
  árbol en una sola operación atómica). Un corte de energía a mitad del paso 4
  puede dejar la instalación con una mezcla de archivos viejos y nuevos; por eso el
  respaldo completo en el paso 3 existe independientemente de si el corte ocurre
  antes o después de un `os.replace` individual — la recuperación asumida es
  "reinicia el procedimiento completo desde el respaldo", no una reanudación fina.
  NTFS no se usa en modo transaccional (la API `TxF` está obsoleta en Windows).
- **Idempotencia no garantizada entre corridas**: cada intento crea sus propios
  `staging-<timestamp>/` y `rollback-<timestamp>/`; no se limpian automáticamente,
  ni se reutilizan entre corridas. La limpieza de `work_dir` es responsabilidad de
  quien orqueste el actualizador real.
