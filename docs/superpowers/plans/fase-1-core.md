# Fase 1 — Core: plan ejecutable

Depende de: Fase 0 (`core/db`, `core/money`, `core/errors`, `core/operations`). Spec §5 y plan de área `2026-09-25-base-core.md`.

## Convenciones de la fase

- Tablas del Core con prefijo `core_`. Modelos en `src/sistemashn/core/<área>/models.py`, heredan `sistemashn.core.db.base.Base`.
- Las pruebas crean el esquema con `Base.metadata.create_all(engine)` sobre una base temporal (fixture común en `tests/conftest.py`: `engine`, `session_factory`, `now` fijo). La migración Alembic de la fase la genera el jefe al cerrar y una prueba verifica que `upgrade head` coincide con los modelos (`compare_metadata` sin diferencias).
- Las migraciones de sonda (0001/0002) se mueven a `tests/fixtures/probe_migrations/` y la cadena real empieza en `0001_core`.
- Tiempo inyectable: los servicios reciben `clock: Callable[[], datetime]` (UTC aware), por defecto `utcnow`.
- Todo servicio público: `def op(self, actor: Actor, ...)`, abre su transacción con `run_in_transaction`, llama `authorizer.require(session, actor, "permiso")` al inicio y registra auditoría **en la misma sesión**.

## Contratos compartidos

```python
# core/authorization/actor.py
@dataclass(frozen=True)
class Actor:
    user_id: int
    username: str
    is_admin: bool
    session_id: str          # uuid de la sesión de login

SYSTEM_ACTOR = Actor(0, "sistema", True, "system")   # solo tareas internas (primer arranque, migraciones)

# core/modules/contracts.py
@dataclass(frozen=True)
class PermissionDef: code: str; label: str; group: str; sensitive: bool = False
@dataclass(frozen=True)
class ProfileDef: code: str; label: str; permissions: frozenset[str]
@dataclass(frozen=True)
class ScreenDef: route: str; label: str; icon: str; permission: str | None; group: str; order: int
    # build: Callable[[AppContext], ft.Control] vive en ui, registrado aparte por route
@dataclass(frozen=True)
class ModuleDef: code: str; label: str; permissions: tuple[PermissionDef, ...];
    profiles: tuple[ProfileDef, ...]; screens: tuple[ScreenDef, ...]

class ModuleRegistry:
    def register(self, module: ModuleDef) -> None      # códigos únicos, error si se repiten
    def permissions(self) -> dict[str, PermissionDef]
    def profiles(self) -> dict[str, ProfileDef]         # perfiles con permisos inexistentes → error
    def screens(self) -> list[ScreenDef]                 # ordenadas por group/order
```

Permisos Core (módulo `core`): `core.usuarios.ver`, `core.usuarios.gestionar`, `core.auditoria.ver`, `core.ajustes.gestionar`, `core.respaldos.gestionar`, `core.actualizaciones.gestionar`, `core.licencia.ver`. Perfil Core sugerido: `administrador` (todos). El administrador (`is_admin`) tiene todo, incluso permisos futuros.

## Tareas

### T1.1 Registro de módulos y autorización
Archivos: `core/modules/contracts.py`, `core/modules/core_module.py` (ModuleDef del Core), `core/authorization/{actor,models,service}.py`.
- Modelos: `core_user_permission(user_id FK, permission_code, granted bool, PK compuesta)`.
- `Authorizer(registry)`: `effective_permissions(session, user_id) -> frozenset[str]` = permisos del perfil del usuario ± overrides; admin → todos los registrados. `require(session, actor, code)`: relee el usuario (activo, no bloqueado, `permissions_version`), lanza `PermissionDenied` si no tiene; código no registrado → `ValueError` (error de programación). `can(...) -> bool`.
- `set_user_permissions(actor, user_id, profile_code, overrides: dict[str,bool])` requiere `core.usuarios.gestionar`, incrementa `permissions_version`, audita antes/después. Un no-admin no puede otorgar permisos que él no tiene ni tocar a un admin.
- Pruebas: perfil + override otorga/quita; revocación mientras el actor sigue "logueado" → siguiente `require` falla; usuario inactivo → PermissionDenied; registro con código duplicado o perfil con permiso inexistente → error.

### T1.2 Identidad (∥ con T1.3 tras T1.1)
Archivos: `core/identity/{models,passwords,service,recovery}.py`.
- `core_user(id, username único en minúsculas, full_name, password_hash, is_admin, is_active, profile_code, permissions_version, failed_attempts, locked_until, must_change_password, created_at, updated_at)`.
- `core_login_session(id uuid, user_id, started_at, ended_at)`; `core_recovery_code(id, code_hash, created_at, used_at, used_by_user_id)`; `core_recovery_challenge(id, nonce, issued_at, used_at)`.
- `passwords.py`: `hash_password`, `verify_password` (argon2 `PasswordHasher`, rehash si `check_needs_rehash`). Política: mínimo 8 caracteres.
- `IdentityService`: `create_user(actor, data)`, `update_user`, `deactivate_user` (no el último admin activo), `change_password(actor, old, new)`, `reset_password(actor, user_id, new)` (gestionar), `login(username, password) -> Actor` (5 fallos → bloqueo 5 min; mensajes que no revelan si existe el usuario; registra fallo en `core_auth_failure(username_intentado, occurred_at, reason)` sin contraseña), `logout(actor)`.
- `recovery.py`: `generate_recovery_codes(session, n=8) -> list[str]` (formato `XXXX-XXXX-XXXX`, base32 sin ambiguos, se guardan solo hashes argon2; regenerar invalida los anteriores); `recover_with_code(code, new_password)` restablece el admin principal, marca el código usado, audita. Desafío del vendedor: `create_recovery_challenge() -> str` (texto copiable con installation_id + nonce), `recover_with_vendor_authorization(token, new_password, public_key)` verifica firma Ed25519 sobre `{"challenge_nonce","installation_id","action":"reset_admin"}`, nonce pendiente y < 72 h, un solo uso.
- Pruebas: hash nunca en claro; bloqueo y desbloqueo por tiempo; código de recuperación usado dos veces falla; token firmado con otra clave o para otra instalación falla; último admin no se desactiva.

### T1.3 Auditoría (∥ con T1.2)
Archivos: `core/audit/{models,service}.py`.
- `core_audit_event(id, occurred_at, user_id nullable, username, session_id, action, entity_type, entity_id, summary, detail_json)`. Triggers SQLite `BEFORE UPDATE`/`BEFORE DELETE` que hacen `RAISE(ABORT, 'audit is append-only')` (crear con `event.listen(table, "after_create", DDL(...))` y replicar en la migración).
- `audit(session, actor, action, entity_type=None, entity_id=None, summary="", detail: dict | None = None)` — mismo `session`, sin commit propio. `detail` se serializa con un encoder que soporta Decimal/datetime y **rechaza** claves `password`, `password_hash`, `code`.
- `AuditQueryService.list(actor, filtros, page, page_size) -> Page[AuditEventView]` requiere `core.auditoria.ver`. `Page` genérica en `core/pagination.py` (`items, total, page, page_size`).
- Pruebas: rollback de la transacción de negocio elimina también su evento; update/delete directo falla; detalle con Decimal; claves prohibidas → ValueError; paginación.

### T1.4 Licencia offline (∥ independiente)
Archivos: `core/licensing/{fingerprint,license,keys,service,models}.py`, `tools/vendor/vendedor.py`, `tools/vendor/README.md`.
- `fingerprint.py`: `machine_fingerprint() -> str` = sha256 hex de `MachineGuid` (winreg `HKLM\SOFTWARE\Microsoft\Cryptography`) + número de serie del volumen del sistema (ctypes `GetVolumeInformationW`); fallback documentado fuera de Windows (`platform.node()`), marcado como no apto para producción.
- Formato: texto `SHN1.<payload_b64url>.<firma_b64url>`; payload JSON canónico (`sort_keys`, separadores compactos, UTF-8): `{license_id, vertical, business_name, installation_id, fingerprint, edition:"perpetua", issued_at, format:1}`. Firma Ed25519 sobre los bytes del payload.
- `keys.py`: `VENDOR_PUBLIC_KEYS: dict[str, bytes]` (id de clave → clave pública raw 32 bytes); la clave de desarrollo se genera con `vendedor.py keygen` y su privada queda en `tools/vendor/keys/` (ignorado por git).
- `ActivationRequest`: `request_code(installation_id, vertical) -> str` (`SHNREQ1.<b64url JSON {installation_id, vertical, fingerprint, app_version}>`).
- `LicenseService`: `verify(text, *, expected_vertical, installation_id, fingerprint, public_keys) -> LicenseInfo` o `LicenseError` con motivo (`firma`, `formato`, `vertical`, `maquina`, `instalacion`); `install(text)` guarda en `core_license(id, raw_text, license_id, installed_at)`; `current()`. El reloj **no** influye en la validez (perpetua).
- `vendedor.py` (argparse): `keygen --out tools/vendor/keys`, `sign-license --request SHNREQ1... --business "Nombre" --key ...`, `sign-recovery --challenge ... --key ...`. Nunca importado por `src/`.
- Pruebas: firma válida; byte alterado; otra clave; otra huella/instalación/vertical; reloj adelantado/atrasado sin efecto; request code ida y vuelta; `vendedor.py` extremo a extremo con `subprocess` y claves en `tmp_path`.

### T1.5 Ajustes e instalación / primer arranque (tras T1.2–T1.4)
Archivos: `core/settings/{models,service}.py`, `core/setup/{models,service}.py`.
- `core_installation(id=1, installation_id uuid, vertical, setup_step, created_at, completed_at)`; `core_business(id=1, name, legal_name, rtn, address, phone, email, logo_path, prices_include_isv=True, fiscal_enabled=False, updated_at)`; `core_setting(key PK, value_json)`.
- `SetupService`: pasos `license → business → admin → recovery → done`; `state()`, `submit_license(text)`, `submit_business(data)` (logo copiado a `data_dir/logo.<ext>`, PNG/JPG ≤ 2 MB), `create_admin(data) -> list[str]` (crea admin y devuelve códigos de recuperación en la misma transacción), `confirm_recovery_codes_saved()` → `done`. Cada paso es su propia transacción; reinicio retoma el paso; tras `done` todo `submit_*` lanza error. Actor `SYSTEM_ACTOR` en auditoría.
- `SettingsService`: `get_business()`, `update_business(actor, data)` (`core.ajustes.gestionar`), `get/set(key)` tipado con Pydantic.
- Pruebas: flujo completo; interrupción entre pasos; repetir tras done; admin con contraseña débil; logo inválido.

### T1.6 UI shell (tras T1.1–T1.5)
Archivos: `core/ui/{theme,app_context,shell,router,widgets,login_view,setup_view,users_view,audit_view,business_view}.py`, `app/repuestos.py`.
- `theme.py`: tokens Grafito y Vino (`PRIMARY #8B2635`, `PRIMARY_DARK #6E1E2A`, `SIDEBAR #27272A`, `CONTENT_BG #FAFAF9`, éxito/advertencia/error/info) y `build_theme()`.
- `AppContext`: session_factory, registry, authorizer, servicios, `actor | None`, `clock`, `data_dir`.
- `router.py`: `Router(registry, screen_builders: dict[route, builder])`; `visible_screens(actor)`; `navigate(route)` verifica permiso **otra vez** y muestra "Sin permiso" si no; sin sesión → login.
- `shell.py`: barra lateral oscura con logo/nombre del negocio, grupos de pantallas visibles, usuario actual y "Cerrar sesión"; área de contenido; `widgets.py`: `empty_state`, `error_banner`, `loading`, `confirm_dialog`, `paginated_table`, `money_text`.
- Pantallas: asistente de primer arranque (4 pasos, muestra código de solicitud copiable, pega licencia, datos de negocio, admin, códigos para anotar con casilla de confirmación); login; usuarios (lista, crear/editar, perfil + ajustes de permisos, desactivar, restablecer contraseña); auditoría (filtros + paginación); ajustes de negocio.
- `app/repuestos.py`: compone `ModuleRegistry` con Core (y luego Comercial/Repuestos), abre base en `data_dir()`, ejecuta `migrate.upgrade`, decide asistente vs login.
- Pruebas: lógica de `Router` sin ventana (pantallas visibles por actor, ruta prohibida denegada); construcción de cada vista con contexto falso no lanza. Verificación manual: arrancar con `evn\Scripts\python.exe src\main.py` y `SISTEMASHN_DATA_DIR` temporal.

## Salida de fase
Suite verde; migración `0001_core` coincide con modelos; recorrido manual: primer arranque con licencia firmada por `vendedor.py`, login admin, crear empleado con perfil restringido, verificar menú oculto y servicio denegado, recuperación con código auditada. Commit `feat: fase 1 core`.
