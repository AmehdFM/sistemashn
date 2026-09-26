# SistemasHN: etapa 0, viabilidad Windows — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** demostrar con una aplicación pequeña que Flet, SQLite/Alembic, respaldo y actualización recuperable funcionan en Windows 10+ y medirlos en el equipo objetivo antes de construir Core comercial.

**Architecture:** una sonda Flet usa un servicio de persistencia SQLite aislado del control visual. El ejecutable y los datos viven en directorios distintos. La actualización de ensayo opera sobre copias, registra versión, verifica integridad y recupera binario y base juntos si falla. La decisión final depende de una prueba en Windows hecha por el dueño.

**Tech Stack:** Python 3.14.x, Flet, SQLAlchemy 2.x, SQLite, Alembic, pytest; empaquetado principal candidato `flet build windows`.

**Spec:** `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`

## Global Constraints

- Windows 10 o superior, una PC, un monitor y una instancia; sin red para operación y restauración local.
- Objetivo de prueba: 4 GB de RAM, CPU básica y HDD; la aceptación de rendimiento corresponde al dueño tras medir su máquina.
- Datos fuera del directorio del programa, una sesión SQLAlchemy por tarea/hilo, claves foráneas activas, escrituras cortas y respaldo SQLite consistente.
- No migrar código ni datos del producto anterior. La etapa 0 no incluye usuarios, licencia, ventas, documentos fiscales ni UI comercial.
- Ningún ensayo de actualización sobre datos reales. El paquete de sonda es local y no habilita todavía órdenes remotas.
- Commits pequeños en rama de trabajo derivada de `desarrollo`; no declarar viable el instalador Windows desde Linux.

## Review Focus

1. Ruta con espacios y caracteres acentuados: la sonda crea, abre y respalda la base en esa ruta (tareas 1 y 2).
2. Segunda instancia y base ocupada: la operación de escritura termina con resultado controlado sin corrupción (tarea 2).
3. Copia con escritura concurrente: el respaldo pasa `PRAGMA integrity_check` y conserva datos confirmados (tarea 3).
4. Paquete dañado o migración fallida: el actualizador rechaza o revierte sin mezclar binario y esquema (tarea 3).
5. Reinicio offline en Windows después de actualizar: la sonda muestra versión y registro previo sin descargar nada (tarea 4).

## Mapa de archivos

| Ruta | Responsabilidad |
|---|---|
| `pyproject.toml`, archivo de bloqueo elegido | Dependencias y comandos reproducibles de la sonda |
| `src/sistemashn/probe/app.py`, `__main__.py` | UI mínima y entrada de la sonda |
| `src/sistemashn/core/db/engine.py`, `session.py`, `models.py` | Motor, vida de sesión y único registro de prueba |
| `alembic.ini`, `migrations/env.py`, `migrations/versions/*` | Dos esquemas de ensayo con datos preservados |
| `src/sistemashn/core/operations/backup.py`, `restore.py`, `probe_update.py`, `contracts.py` | Snapshot, verificación, restauración de ensayo y reversión |
| `tests/probe/*`, `tests/db/*`, `tests/operations/*` | Pruebas de comportamiento, integridad y fallo |
| `docs/decisions/*`, `docs/validation/*`, `scripts/measure_stage0.ps1` | Decisiones técnicas y evidencia de Windows |

---

### Task 1: base reproducible y ventana Flet mínima

**Files:**
- Create: `pyproject.toml`, archivo de bloqueo de la herramienta elegida, `src/sistemashn/__init__.py`, `src/sistemashn/probe/__init__.py`, `src/sistemashn/probe/app.py`, `src/sistemashn/probe/__main__.py`
- Create: `tests/probe/test_app.py`, `docs/decisions/001-stage0-toolchain.md`
- Modify: `docs/README.md` para enlazar este plan y aclarar su estado

**Interfaces:**
- Produces: `build_probe_view(version: str) -> ft.Control` con una etiqueta de versión y un control que responde a un clic; `main(page: ft.Page) -> None` monta la vista. El ejecutable acepta una ruta de datos configurable por argumento o configuración externa; nunca escribe la base dentro del paquete.
- El ADR registra intérprete, versión real de cada dependencia, herramienta y comando de build, versión de Flutter empleada, arquitectura x64 y modo de bloqueo. Las versiones se fijan tras instalar y probar, sin asumir que un metadato de PyPI garantice funcionamiento.

- [ ] **Step 1: Escribir prueba fallida** en `tests/probe/test_app.py`: `build_probe_view("0.1")` contiene texto `SistemasHN 0.1`, ofrece una acción y su activación cambia un indicador observable sin ventana nativa; incluir una prueba de importación desde ruta con espacios.
- [ ] **Step 2: Confirmar rojo:** `python -m pytest tests/probe/test_app.py -v` falla por interfaz ausente.
- [ ] **Step 3: Crear empaquetado Python y sonda Flet mínima** con las firmas anteriores. Mantener UI y acceso a datos separados; instalar el proyecto en modo editable y registrar versiones resueltas en bloqueo y ADR.
- [ ] **Step 4: Confirmar verde:** `python -m pytest tests/probe/test_app.py -v`; `python -m sistemashn.probe` abre una ventana en un entorno con pantalla. Registrar el comando real sin afirmar que el Codespace prueba Windows.
- [ ] **Step 5: Commit:** `git add pyproject.toml src tests/probe docs/README.md docs/decisions archivo-de-bloqueo` y `git commit -m "feat: scaffold Windows feasibility probe"` (sustituir el nombre descriptivo del bloqueo).

### Task 2: SQLite con sesiones y dos migraciones de ensayo

**Files:**
- Create: `src/sistemashn/core/db/{__init__,engine,session,models}.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_probe_schema.py`, `migrations/versions/0002_probe_schema_change.py`
- Create: `tests/db/test_engine.py`, `tests/db/test_migrations.py`

**Interfaces:**
- Produces: `create_engine_for_path(path: Path) -> Engine` activa `PRAGMA foreign_keys=ON` y `busy_timeout` por conexión, documenta journal/synchronous escogidos; `session_scope(engine: Engine) -> Iterator[Session]` confirma o revierte y cierra cada sesión.
- `0001` crea `probe_records(id, value)`; `0002` añade una columna `note` con valor por defecto que conserva los registros existentes. La base de prueba pertenece a una ruta externa al paquete.

- [ ] **Step 1: Escribir pruebas fallidas:** FK activa en cada conexión; dos sesiones separadas; un error dentro de `session_scope` no deja escritura; ruta con espacios/acentos; bloqueo de una segunda conexión produce error controlado tras espera finita. La prueba de migración crea un registro en `0001`, actualiza a `0002`, baja a `0001` y vuelve a subir conservando `id` y `value`.
- [ ] **Step 2: Confirmar rojo:** `python -m pytest tests/db -v` falla por módulos o migraciones ausentes.
- [ ] **Step 3: Implementar motor, sesiones y migraciones** con la configuración explicitada en `docs/decisions/001-stage0-toolchain.md`; no compartir sesiones entre hilos.
- [ ] **Step 4: Confirmar verde:** `python -m pytest tests/db -v`; registrar `alembic history` y `alembic current` para una base temporal con datos.
- [ ] **Step 5: Commit:** `git add src/sistemashn/core/db alembic.ini migrations tests/db docs/decisions/001-stage0-toolchain.md && git commit -m "feat: add probe persistence and migrations"`.

### Task 3: respaldo y actualización local recuperable

**Files:**
- Create: `src/sistemashn/core/operations/{__init__,contracts,backup,restore,probe_update}.py`, `tests/operations/test_backup_restore.py`, `tests/operations/test_probe_update.py`, `docs/decisions/002-stage0-recovery-contract.md`

**Interfaces:**
- Produces: `create_backup(source: Path, destination: Path) -> BackupReceipt` usa `sqlite3.Connection.backup`, cierra conexiones y verifica integridad; `verify_backup(path: Path) -> VerificationResult` informa resultado de `PRAGMA integrity_check`, hash y versión; `restore_to_trial(backup: Path, trial_db: Path) -> RestoreResult` rehúsa sobrescribir una base existente por defecto.
- Produces: `apply_probe_update(package: Path, installation: Path, data_dir: Path) -> UpdateResult` para un paquete ZIP de ensayo con manifiesto y hashes. Antes de sustituir, copia versión instalada y respalda/verifica base; aplica `0001→0002`, comprueba la sonda y confirma versión. Ante error recupera ejecutable y base coherentes. Se documenta que esto no constituye aún el formato firmado ni el actualizador remoto del producto.

- [ ] **Step 1: Escribir pruebas fallidas de respaldo:** datos confirmados mientras otra conexión está abierta, snapshot íntegro y restauración de ensayo; archivo corrupto rechazado; destino existente preservado; ruta con espacios/acentos.
- [ ] **Step 2: Escribir pruebas fallidas de actualización:** manifiesto/hash inválido no toca la instalación; migración o prueba de arranque inducidamente fallida restaura versión y registro anteriores; ejecución correcta conserva registro y llega a `0002`. Comparar versión, hash y `integrity_check` antes y después.
- [ ] **Step 3: Confirmar rojo:** `python -m pytest tests/operations -v` falla por operaciones ausentes.
- [ ] **Step 4: Implementar contratos y operaciones** con directorio de preparación separado, reemplazo seguro dentro de los límites de este ensayo y registro de recuperación. Una actualización real futura requiere firmas, proceso externo y ensayo de NTFS; no prometer reversibilidad universal de migraciones.
- [ ] **Step 5: Confirmar verde:** `python -m pytest tests/operations -v` y luego `python -m pytest -v`. Registrar los límites y procedimiento exacto en el ADR.
- [ ] **Step 6: Commit:** `git add src/sistemashn/core/operations tests/operations docs/decisions/002-stage0-recovery-contract.md && git commit -m "feat: probe consistent backup and update rollback"`.

### Task 4: paquete Windows y decisión de viabilidad

**Files:**
- Create: configuración necesaria para `flet build windows`, `scripts/measure_stage0.ps1`, `docs/validation/stage-0-codespace.md`, `docs/validation/stage-0-windows.md`, `docs/validation/stage-0-results.md`
- Modify: `docs/decisions/001-stage0-toolchain.md` con comando final reproducible

**Interfaces:**
- `measure_stage0.ps1` recibe ruta del ejecutable y directorio de salida; registra cinco arranques, memoria en reposo, versión/hardware/Windows y resultado de interacción manual. No fija umbral de rendimiento no acordado; produce mediciones para decisión del dueño.
- La checklist Windows cubre checkout limpio, build x64, instalación, separación binario/datos, inicio sin red, ruta Unicode, teclado/DPI, actualización local desde ZIP, fallo inducido, restauración de ensayo y segundo inicio offline. Cada resultado tiene estado `Pasa`, `Falla` o `No probado`, evidencia y observación.

- [ ] **Step 1: Escribir comprobación automatizada del script** para argumentos inexistentes y salida estructurada (por ejemplo una invocación PowerShell en Windows); no fingir ejecución de PowerShell Windows en Codespace.
- [ ] **Step 2: Implementar configuración de build y script**, documentando prerequisitos reales, artefacto, comando, tamaño/hash y modo offline; generar checklist y plantilla de resultados sin marcar pruebas Windows no ejecutadas.
- [ ] **Step 3: Verificar en Codespace:** `python -m pytest -v`, `git diff --check`, importación y migraciones. Registrar resultados reales y limitaciones en `stage-0-codespace.md`.
- [ ] **Step 4: Entregar al dueño el procedimiento Windows:** construir y ejecutar en su máquina Windows 10+ con 4 GB/HDD o la más cercana, cinco arranques, memoria, respuesta al control, backup/restauración y actualización/fallo. El dueño registra aceptación o rechazo del rendimiento en `stage-0-results.md`.
- [ ] **Step 5: Cerrar puerta:** sólo con resultados Windows observados, clasificar `Viable`, `Bloqueado` o `Requiere rediseño`; si falta prueba, dejar `Pendiente`, sin iniciar etapa 1.
- [ ] **Step 6: Commit:** `git add scripts docs/validation docs/decisions/001-stage0-toolchain.md configuración-de-build && git commit -m "docs: record Windows stage zero validation"`.

## Límites y siguiente etapa

La sonda prueba un mecanismo pequeño, no la seguridad del actualizador firmado, las normas fiscales, impresoras ni una migración futura arbitraria. La etapa 1 empieza sólo tras decisión documentada sobre Windows. Los planes por área siguen siendo la guía de alcance y se desglosan en tareas equivalentes antes de cada implementación.
