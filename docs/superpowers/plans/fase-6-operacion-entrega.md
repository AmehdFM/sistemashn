# Fase 6 — Operación y entrega: plan ejecutable

Depende de: Fases 1-5 completas. Plan de área `2026-09-25-operacion-entrega.md`, ADR-003
(contrato de actualización de ensayo de Etapa 0), spec `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`.

## Decisiones de la fase

- **Lo que se puede codificar y probar aquí (Linux, sin Windows/Flutter/VS2022/impresora real) vs.
  lo que solo se documenta**: la pantalla de respaldos, el firmado Ed25519, el extender del
  contrato ADR-003 y el proceso `updater/` son código Python puro, verificable con pytest en
  cualquier plataforma. `flet build windows`, Inno Setup, PyInstaller de un `.exe` de Windows y la
  prueba de impresora real NO se pueden ejecutar ni verificar en este entorno: los scripts se
  escriben y se documentan, pero su ejecución y verificación real las hace el propietario en su PC
  Windows, igual que ya se hizo en Etapa 0 (`docs/validation/stage-0-windows.md`). No se afirma
  aquí que un build o instalador "funciona" sin haberlo corrido en Windows.
- **Actualización obligatoria remota**: por instrucción del plan general, esta fase NO la
  codifica. Se documenta como diseño pendiente (canal, identidad de instalación, antirreplay,
  gestión de claves) en la sección T6.5 de este plan, sin implementación.
- **Extiende ADR-003, no lo reemplaza**: el paquete de actualización real añade **firma Ed25519**
  del manifiesto (misma familia de claves que `tools/vendor/` usa para licencias, un `key_id`
  separado, p. ej. `update-2026`, agregado a un nuevo `UPDATE_PUBLIC_KEYS` en
  `core/licensing/keys.py` o un módulo hermano `core/updater/keys.py` — decidir y documentar) y
  verificación de esa firma ANTES de `validate_package` (si la firma no es válida, se rechaza el
  paquete exactamente igual que un manifest corrupto, sin tocar disco). El resto del contrato
  (estructura del ZIP, `apply_probe_update`, rollback) NO cambia: se reutiliza literalmente, solo
  se le antepone la verificación de firma.
- **Proceso `updater/` separado**: un ejecutable aparte (empaquetado con PyInstaller onefile en
  Windows) que la app principal invoca y del que se despide antes de cerrar. Espera a que el
  proceso de la app termine (poll de PID o un archivo de bloqueo que la app borra al salir —
  decidir el más simple: archivo de bloqueo, ya que no depende de permisos de acceso a otro
  proceso en Windows), aplica el paquete ya validado y descargado por la app (la app hace la
  descarga/selección de ZIP y la validación de firma; el `updater` solo ejecuta
  `apply_probe_update` fuera del proceso de la app), reintenta una vez si el primer intento falla
  antes de reportar error, y al reiniciar deja un log que la app lee en su siguiente arranque para
  mostrar el resultado.
- **Respaldo real reemplaza el placeholder**: `core/ui/views/backups_placeholder.py` se sustituye
  por una pantalla real sobre `core/operations/backup.py`/`restore.py` (ya existen y están
  probados desde Etapa 0, no se tocan). Recordatorio diario: se guarda la fecha del último respaldo
  verificado en `core_setting` (clave `ultimo_respaldo_verificado`, ya existe el mecanismo
  genérico clave/valor) y se compara al montar el shell (`app_shell.py`); si pasaron ≥ 24 h o no
  hay ninguno, se muestra un aviso no bloqueante (banner, no diálogo modal) — persiste aunque la
  PC haya estado apagada porque se calcula por fecha, no por temporizador en memoria.
- **Actualización manual desde ZIP**: la pantalla de respaldos/actualizaciones ofrece "Buscar
  actualización" (deshabilitado si no hay conector de red configurado — fuera de alcance de este
  plan tener un servidor real de actualizaciones, se documenta como pendiente igual que la
  obligatoria remota) y "Aplicar paquete local (ZIP)" que sí es código real y probable: el
  administrador elige un `.zip` con `ft.FilePicker` (mismo patrón que `widgets.file_picker` de la
  Fase 3), se valida la firma y el manifiesto, se muestra un resumen (versión origen/destino,
  archivos a reemplazar) y se pide confirmación antes de invocar al `updater`.

## Tareas

### T6.1 Pantalla de respaldos real (`core/ui/views/`, reemplaza `backups_placeholder.py`)

- `BackupService` (nuevo, envuelve `operations/backup.py`/`restore.py` con permisos/auditoría —
  hoy esas funciones son de bajo nivel sin `Actor` ni permisos; el servicio nuevo sí los exige:
  `core.respaldos.gestionar`, agregar a `core/modules/core_module.py`): `create(actor, dest_dir) ->
  BackupResult` (usa `create_backup`, guarda fecha en `core_setting`), `verify(actor, backup_path)
  -> VerifyResult` (usa `verify_backup`), `restore_to_trial(actor, backup_path, trial_dir) ->
  RestoreResult` (ensayo, nunca sobre la base activa), `last_verified_at(actor) -> datetime |
  None`, `history(actor) -> list[BackupRecord]` (lista de respaldos conocidos — guardar un
  registro simple en `core_setting` como JSON de lista, o una tabla nueva `core_backup_record` si
  crece; decidir el más simple y documentar).
- Pantalla: historial (fecha, destino, verificado sí/no), botón "Respaldar ahora" (elige carpeta
  destino con `FilePicker.get_directory_path`), botón "Verificar" por fila, botón "Restaurar en
  ensayo" (pide una carpeta de ensayo, nunca sobrescribe la instalación activa, muestra resultado),
  recordatorio si `last_verified_at` es `None` o tiene más de 24 h.
- Pruebas: crear/verificar/listar; restaurar en ensayo no toca `ctx.data_dir` real; recordatorio
  aparece/desaparece según `last_verified_at`; permisos.

### T6.2 Paquete de actualización firmado (`core/updater/` en el paquete `core`, sin depender de
Comercial/Repuestos)

- `core/updater/keys.py`: `UPDATE_PUBLIC_KEYS: dict[str, bytes]` (mismo patrón que
  `core/licensing/keys.py`, clave de desarrollo separada `update-2026`).
- `core/updater/package.py`: extiende `core/operations/probe_update.py` (o lo reemplaza,
  documentar la decisión) agregando `verify_signature(zip_path, public_keys) -> None` (lanza
  `InvalidPackageError` si la firma del manifiesto no es válida o no existe) ANTES de
  `validate_package`; el manifiesto ahora incluye un campo `signature` (firma Ed25519 del resto
  del JSON canonicalizado, mismo `codec.sign`/`codec.verify_signed` que usan licencias — reutilizar
  `sistemashn.core.licensing.codec`, que ya es genérico de Core).
- `tools/vendor/vendedor.py`: agrega subcomando `sign-update --manifest <ruta> --key <priv> --key-id
  <id>` que firma un `manifest.json` y lo reescribe con el campo `signature`.
- Pruebas: firma inválida rechazada antes de tocar disco (extiende las pruebas ya existentes de
  `probe_update`); firma válida con clave desconocida rechazada; paquete truncado/corrupto sigue
  rechazado igual que antes (no se rompe el contrato ADR-003 existente).

### T6.3 Proceso `updater/` (entrada para PyInstaller)

- `src/sistemashn/updater/__main__.py` (o `updater/main.py` con `src/updater_main.py` delgado para
  PyInstaller, mismo patrón que `src/main.py` → `sistemashn.app.repuestos.main`): recibe por
  argumentos la ruta del paquete ya validado, la instalación y la base; espera un archivo de
  bloqueo (`<data_dir>/.app.lock`, que la app crea al iniciar y borra al salir limpio — si no se
  borró, ya se asume cierre limpio tras N segundos de que el proceso de la app ya no aparece en la
  lista, usando `psutil` NO está permitido si no está en `requirements.txt`: usar en su lugar
  comprobación de PID vía `os.kill(pid, 0)` con manejo de `OSError`/`ProcessLookupError`, sin
  dependencias nuevas); aplica `apply_probe_update` (o su sucesor firmado); reintenta UNA vez si
  falla; escribe el mismo `update-log.jsonl` de ADR-003; al terminar, si hay éxito, puede volver a
  lanzar la app (`subprocess.Popen`) o dejar que el usuario la abra manualmente — decidir el más
  simple para v1 (no relanzar automáticamente, mostrar instrucción) y documentarlo.
- Pruebas: simula "app cerrada" (sin archivo de bloqueo) y aplica; simula "app viva" (bloqueo
  presente, PID válido) y espera/reintenta hasta un límite antes de fallar con mensaje claro; un
  fallo de aplicación reintenta una vez y luego revierte (reutiliza las pruebas de rollback ya
  existentes de `probe_update`, extendidas al flujo de reintento).

### T6.4 Actualización manual desde ZIP (UI)

- Pantalla (extiende la de T6.1 o una pestaña aparte "Actualizaciones" en el mismo lugar):
  `widgets.file_picker` para elegir el ZIP, muestra el resumen del manifiesto verificado (versión
  origen → destino, archivos, `schema_revision`) antes de confirmar, botón "Aplicar" que cierra la
  app y lanza `updater/` con los argumentos correspondientes (`subprocess.Popen` + `page.window
  .close()` o `sys.exit`, verificar el mecanismo real de cierre limpio que ya usa la app, si
  existe uno). "Buscar actualización por internet" queda deshabilitado con el texto "requiere
  configurar un servidor de actualizaciones (pendiente)" — no se implementa un backend remoto en
  esta fase.
- Pruebas: la pantalla construye sin lanzar con y sin permiso; el resumen del manifiesto se
  muestra correctamente para un ZIP de prueba válido/ inválido (reutiliza fixtures de
  `probe_update`).

### T6.5 Actualización obligatoria remota — diseño pendiente, NO se codifica

Documentar en esta sección (no en código) antes de intentar una versión futura:
- **Canal**: HTTPS a un servidor propio (no incluido en este repo); la app hace polling
  periódico opcional, nunca push real sin servidor.
- **Identidad de instalación**: usar el mismo `installation_id` ya generado en `core_setup`
  (Fase 1) como identificador único frente al servidor, sin PII adicional.
- **Antirreplay**: cada orden remota lleva un nonce firmado con expiración corta; la app recuerda
  los últimos nonces aplicados (tabla nueva, no existe todavía) para rechazar repeticiones.
- **Claves**: mismo esquema Ed25519 de `tools/vendor/`, un `key_id` dedicado a órdenes remotas,
  rotable independientemente de las claves de licencia/actualización de paquete.
- **Comportamiento esperado**: la orden se aplica solo tras terminar la operación activa (venta,
  pago, migración, respaldo en curso); un equipo desconectado la recibe recién al reconectar, sin
  reintentos agresivos que interrumpan el uso normal.
- Ninguna prueba automatizada de este punto: es diseño para una fase futura.

### T6.6 Scripts de entrega (no se ejecutan aquí, se escriben para Windows)

- `scripts/build_windows.ps1`: `flet build windows` con `$env:PYTHONIOENCODING="utf-8"`, salida a
  `build/windows`, copia el resultado a una carpeta de entrega con el `VERSION` actual.
- `scripts/build_updater.ps1`: PyInstaller onefile de `src/updater_main.py` (o el entrypoint que
  se decida en T6.3) a `dist/updater.exe`.
- `installer/sistemashn.iss` (Inno Setup): instala el programa en `Program Files`, datos de
  usuario en `%LOCALAPPDATA%\SistemasHN\repuestos` (ya es la ruta real usada por
  `core/db/engine.py` desde Fase 0/1, no se cambia), desinstalar conserva los datos (no borra
  `%LOCALAPPDATA%`), incluye `updater.exe` junto al programa.
- `tools/vendor/vendedor.py sign-update`: ya cubierto en T6.2.
- Estos tres archivos se escriben con cuidado (comentarios explicando cada paso) pero no se
  ejecutan ni se afirma que producen un instalador funcional sin probarlo en Windows — eso queda
  para el propietario, igual que el build de Etapa 0.

### T6.7 Manual de operación

`docs/manual-operacion.md`: activación (usar `activar_licencia.py` en desarrollo; en producción,
el flujo real de primer arranque con el vendedor), respaldo (dónde, cada cuánto, cómo verificar),
restauración (ensayo primero, nunca sobre la base activa sin respaldo previo), actualización
(normal por ZIP, qué hacer si falla y revierte), soporte (desafío/token de recuperación de
administrador, ya implementado desde Fase 1), reactivación por cambio de hardware (procedimiento
manual con el vendedor, la licencia está atada a la huella de máquina — ver
`core/licensing/fingerprint.py`). Sin afirmaciones de cumplimiento fiscal ni de rendimiento no
medido en el hardware objetivo del cliente final (solo lo medido en Etapa 0 en la PC del
propietario).

## Migración

Ninguna tabla nueva de negocio si `core_backup_record`/nonces remotos se implementan como
`core_setting` JSON (decisión de T6.1/T6.5); si se opta por tablas dedicadas, agregar
`0005_operacion.py` siguiendo el mismo patrón que las migraciones anteriores.

## Salida de fase — recorrido de aceptación integral

Instalar sin internet (en Windows, por el propietario); activar con licencia offline; crear
negocio y administrador; crear empleado restringido; importar productos y asociar piezas;
registrar compra a crédito y abono; cotizar y apartar con vencimiento; vender kit y pieza con
pagos mixtos y costo conservado; emitir comprobante genérico (factura legal permanece
deshabilitada salvo que el propietario configure una autorización real y decida activarla);
abonar venta a crédito; devolver parcialmente una pieza defectuosa con saldo a favor; cerrar caja;
exportar reportes; respaldar, restaurar en ensayo y actualizar desde paquete ZIP local firmado.
Comprobar que un rol restringido no ve ni puede invocar servicios prohibidos. Simular interrupción
en venta, migración y actualización sin dejar estados parciales. Commit `feat: fase 6 operacion y
entrega`, PAUSA FINAL con la lista de este recorrido para que el propietario la ejecute en su PC.
