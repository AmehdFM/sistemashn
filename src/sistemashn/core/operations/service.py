"""`BackupService`: envuelve `operations/backup.py`/`restore.py` con permisos y auditoría (T6.1).

Vive junto a `backup.py`/`restore.py` porque es la capa de servicio de ese mismo subdominio
(operaciones de mantenimiento de la base), igual que `core/settings/service.py` vive junto a
`core/settings/models.py`. No depende de `SettingsService` para no acoplar un subdominio con
otro dentro de `core`; en su lugar replica el patrón mínimo de `SettingsService.get`/`.set`
(un valor JSON tipado por clave en `core_setting`), documentado aquí explícitamente.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.operations.backup import create_backup, default_backup_name, verify_backup
from sistemashn.core.operations.contracts import BackupReceipt, RestoreResult, VerificationResult
from sistemashn.core.operations.restore import restore_to_trial as _restore_to_trial
from sistemashn.core.settings.models import Setting

#: Único permiso que exige todo el servicio: crear/verificar/restaurar/consultar historial son
#: todas operaciones administrativas sensibles (mismo criterio que el resto de `core.*.gestionar`).
PERMISSION = "core.respaldos.gestionar"

_LAST_VERIFIED_KEY = "ultimo_respaldo_verificado"
_HISTORY_KEY = "historial_respaldos"

#: Nombre fijo de la base restaurada en una carpeta de ensayo: nunca coincide con el nombre real
#: de la base activa (`sistemashn.db`), para que sea imposible restaurar por error sobre ella.
_TRIAL_DB_NAME = "sistemashn-ensayo.db"


class _LastVerified(BaseModel):
    verified_at: datetime


class _BackupRecordModel(BaseModel):
    path: str
    created_at: datetime
    verified: bool
    size_bytes: int


class _BackupHistory(BaseModel):
    records: list[_BackupRecordModel] = []


@dataclass(frozen=True)
class BackupRecord:
    """Proyección de solo lectura de una entrada del historial de respaldos."""

    path: str
    created_at: datetime
    verified: bool
    size_bytes: int


class BackupService:
    """Respaldo, verificación y restauración en ensayo, con permisos y auditoría."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime],
        db_path: Path,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.db_path = db_path

    def _require(self, actor: Actor) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, PERMISSION)

        run_in_transaction(self.factory, _op, readonly=True)

    def _read_history(self, session: Session) -> _BackupHistory:
        fila = session.get(Setting, _HISTORY_KEY)
        return (
            _BackupHistory.model_validate_json(fila.value_json)
            if fila is not None
            else (_BackupHistory())
        )

    def _write_history(self, session: Session, historial: _BackupHistory) -> None:
        value_json = historial.model_dump_json()
        fila = session.get(Setting, _HISTORY_KEY)
        if fila is None:
            session.add(Setting(key=_HISTORY_KEY, value_json=value_json))
        else:
            fila.value_json = value_json

    def _write_last_verified(self, session: Session, verified_at: datetime) -> None:
        value_json = _LastVerified(verified_at=verified_at).model_dump_json()
        fila = session.get(Setting, _LAST_VERIFIED_KEY)
        if fila is None:
            session.add(Setting(key=_LAST_VERIFIED_KEY, value_json=value_json))
        else:
            fila.value_json = value_json

    def create(self, actor: Actor, dest_dir: Path) -> BackupReceipt:
        """Crea un respaldo en `dest_dir` y lo agrega al historial como ya verificado."""
        self._require(actor)

        nombre = default_backup_name(self.clock())
        receipt = create_backup(self.db_path, dest_dir / nombre)

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, PERMISSION)
            historial = self._read_history(session)
            historial.records.append(
                _BackupRecordModel(
                    path=str(receipt.destination),
                    created_at=receipt.created_at,
                    verified=receipt.verification.ok,
                    size_bytes=receipt.verification.size_bytes,
                )
            )
            self._write_history(session, historial)
            self._write_last_verified(session, receipt.created_at)
            session.flush()

            audit(
                session,
                actor,
                "core.respaldo.creado",
                entity_type="core_backup",
                entity_id=str(receipt.destination),
                summary=f"Respaldo creado en {receipt.destination}",
                detail={
                    "destino": str(receipt.destination),
                    "tamaño_bytes": receipt.verification.size_bytes,
                },
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)
        return receipt

    def verify(self, actor: Actor, backup_path: Path) -> VerificationResult:
        """Verifica un respaldo existente y actualiza su entrada de historial (o la agrega)."""
        self._require(actor)

        resultado = verify_backup(backup_path)

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, PERMISSION)
            historial = self._read_history(session)
            ruta = str(backup_path)
            encontrado = False
            nuevos: list[_BackupRecordModel] = []
            for registro in historial.records:
                if registro.path == ruta:
                    registro = registro.model_copy(
                        update={"verified": resultado.ok, "size_bytes": resultado.size_bytes}
                    )
                    encontrado = True
                nuevos.append(registro)
            if not encontrado:
                nuevos.append(
                    _BackupRecordModel(
                        path=ruta,
                        created_at=self.clock(),
                        verified=resultado.ok,
                        size_bytes=resultado.size_bytes,
                    )
                )
            historial.records = nuevos
            self._write_history(session, historial)
            if resultado.ok:
                self._write_last_verified(session, self.clock())
            session.flush()

            audit(
                session,
                actor,
                "core.respaldo.verificado",
                entity_type="core_backup",
                entity_id=ruta,
                summary=f"Respaldo verificado: {'correcto' if resultado.ok else 'con errores'}",
                detail={"ruta": ruta, "ok": resultado.ok, "integridad": resultado.integrity},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)
        return resultado

    def restore_to_trial(self, actor: Actor, backup_path: Path, trial_dir: Path) -> RestoreResult:
        """Restaura `backup_path` en una base de ensayo dentro de `trial_dir`.

        IMPORTANTE: el destino SIEMPRE es `trial_dir / "sistemashn-ensayo.db"`. Este método
        nunca recibe ni usa `self.db_path` como destino: jamás sobrescribe la base activa.
        """
        self._require(actor)

        destino_ensayo = trial_dir / _TRIAL_DB_NAME
        resultado = _restore_to_trial(backup_path, destino_ensayo)

        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, PERMISSION)
            audit(
                session,
                actor,
                "core.respaldo.restaurado_ensayo",
                entity_type="core_backup",
                entity_id=str(backup_path),
                summary=f"Respaldo {backup_path} restaurado en ensayo {destino_ensayo}",
                detail={"respaldo": str(backup_path), "destino_ensayo": str(destino_ensayo)},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)
        return resultado

    def last_verified_at(self, actor: Actor) -> datetime | None:
        """Fecha del último respaldo verificado con éxito, o `None` si no hay ninguno.

        Exige el mismo permiso que el resto del servicio: solo quien puede administrar
        respaldos puede consultar este dato (la pantalla ya está protegida por ese permiso).
        """

        def _op(session: Session) -> str | None:
            self.authorizer.require(session, actor, PERMISSION)
            fila = session.get(Setting, _LAST_VERIFIED_KEY)
            return fila.value_json if fila is not None else None

        value_json = run_in_transaction(self.factory, _op, readonly=True)
        return _LastVerified.model_validate_json(value_json).verified_at if value_json else None

    def history(self, actor: Actor) -> list[BackupRecord]:
        """Historial de respaldos conocidos, más reciente primero."""

        def _op(session: Session) -> _BackupHistory:
            self.authorizer.require(session, actor, PERMISSION)
            return self._read_history(session)

        historial = run_in_transaction(self.factory, _op, readonly=True)
        return [
            BackupRecord(
                path=r.path, created_at=r.created_at, verified=r.verified, size_bytes=r.size_bytes
            )
            for r in reversed(historial.records)
        ]
