"""Lógica del proceso `updater`: espera el cierre de la app y aplica el paquete firmado (T6.3).

Un proceso aparte (empaquetado con PyInstaller onefile en Windows) que la app principal
invoca al cerrar. Espera un archivo de bloqueo con el PID de la app (`.app.lock`, que
la app crea al iniciar y borra al cerrar limpio), y solo entonces aplica el paquete de
actualización ya validado y firmado, fuera del proceso de la app.
"""

import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sistemashn.core.operations.probe_update import UpdateResult
from sistemashn.core.updater.keys import UPDATE_PUBLIC_KEYS
from sistemashn.core.updater.package import apply_signed_update


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return False
    return True


def wait_for_app_exit(
    lock_file: Path,
    *,
    max_wait_seconds: float = 30.0,
    poll_interval: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> bool:
    """Espera a que la app cierre (borre `lock_file` o su PID ya no exista).

    Retorna `True` en cuanto se confirma el cierre; `False` si sigue viva al agotar
    `max_wait_seconds`. Testeable inyectando `sleep`/`now` para no dormir de verdad.
    """
    if not lock_file.exists():
        return True

    inicio = now()
    while True:
        try:
            contenido = lock_file.read_text(encoding="utf-8").strip()
            pid = int(contenido)
        except OSError:
            # El archivo desapareció entre el chequeo y la lectura: cierre en curso.
            return True
        except ValueError:
            # Contenido ilegible como PID: se interpreta como cierre limpio en curso.
            return True

        if not _process_alive(pid):
            return True

        if now() - inicio >= max_wait_seconds:
            return False

        sleep(poll_interval)


def run_update(
    package: Path,
    installation: Path,
    db_path: Path,
    work_dir: Path,
    lock_file: Path,
    *,
    public_keys: dict[str, bytes] | None = None,
    max_wait_seconds: float = 30.0,
    clock: Callable[[], datetime] = _default_clock,
) -> UpdateResult:
    """Espera el cierre de la app, aplica el paquete firmado y reintenta una vez si falla.

    Si la app no cierra a tiempo, retorna un `UpdateResult` con `ok=False` sin intentar
    aplicar nada (se mantiene un único tipo de resultado en toda la ruta de actualización,
    en vez de mezclar excepciones y resultados).

    `apply_probe_update` ya revierte internamente en cada intento propio, así que
    reintentar aquí es simplemente "volver a intentar desde cero" tras un rollback
    limpio, nunca continuar sobre un estado a medias.
    """
    claves = public_keys if public_keys is not None else UPDATE_PUBLIC_KEYS

    if not wait_for_app_exit(lock_file, max_wait_seconds=max_wait_seconds):
        installed_version = (installation / "VERSION").read_text(encoding="utf-8").strip()
        return UpdateResult(
            ok=False,
            from_version=installed_version,
            to_version="",
            error="la aplicación no cerró a tiempo",
            rolled_back=False,
        )

    resultado = apply_signed_update(
        package, installation, db_path, work_dir, public_keys=claves, clock=clock
    )
    if not resultado.ok:
        resultado = apply_signed_update(
            package, installation, db_path, work_dir, public_keys=claves, clock=clock
        )
    return resultado
