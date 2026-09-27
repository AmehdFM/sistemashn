"""Pruebas de BackupService: crear, verificar, restaurar en ensayo, historial y permisos (T6.1)."""

from pathlib import Path

import pytest

from sistemashn.core.authorization.actor import SYSTEM_ACTOR, Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.errors import PermissionDenied
from sistemashn.core.modules.contracts import ModuleDef, ModuleRegistry, PermissionDef, ProfileDef
from sistemashn.core.operations.contracts import DestinationExistsError
from sistemashn.core.operations.service import BackupService

PERMISO_RESPALDOS = PermissionDef("core.respaldos.gestionar", "Gestionar respaldos", "Admin")
PERFIL_ADMINISTRADOR = ProfileDef(
    "administrador", "Administrador", frozenset({PERMISO_RESPALDOS.code})
)
PERFIL_VENDEDOR = ProfileDef("vendedor", "Vendedor", frozenset())


@pytest.fixture
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(
        ModuleDef(
            code="core",
            label="Core",
            permissions=(PERMISO_RESPALDOS,),
            profiles=(PERFIL_ADMINISTRADOR, PERFIL_VENDEDOR),
        )
    )
    return reg


@pytest.fixture
def authorizer(registry, clock) -> Authorizer:
    return Authorizer(registry, clock=clock)


def actor_sin_permiso() -> Actor:
    return Actor(user_id=99, username="vendedor", is_admin=False, session_id="s1")


@pytest.fixture
def db_path(db_engine) -> Path:
    return Path(db_engine.url.database)


@pytest.fixture
def backup_service(session_factory, authorizer, clock, db_path) -> BackupService:
    return BackupService(session_factory, authorizer, clock, db_path)


def test_create_guarda_receipt_e_historial(backup_service, tmp_path):
    destino = tmp_path / "respaldos"
    destino.mkdir()

    receipt = backup_service.create(SYSTEM_ACTOR, destino)

    assert receipt.destination.exists()
    historial = backup_service.history(SYSTEM_ACTOR)
    assert len(historial) == 1
    assert historial[0].path == str(receipt.destination)
    assert historial[0].verified is True


def test_create_sin_permiso_falla(backup_service, tmp_path):
    destino = tmp_path / "respaldos"
    destino.mkdir()

    with pytest.raises(PermissionDenied):
        backup_service.create(actor_sin_permiso(), destino)
    assert backup_service.history(SYSTEM_ACTOR) == []


def test_verify_actualiza_ultimo_verificado(backup_service, tmp_path):
    destino = tmp_path / "respaldos"
    destino.mkdir()
    receipt = backup_service.create(SYSTEM_ACTOR, destino)

    assert backup_service.last_verified_at(SYSTEM_ACTOR) is not None

    resultado = backup_service.verify(SYSTEM_ACTOR, receipt.destination)
    assert resultado.ok is True


def test_verify_sin_permiso_falla(backup_service, tmp_path):
    destino = tmp_path / "respaldos"
    destino.mkdir()
    receipt = backup_service.create(SYSTEM_ACTOR, destino)

    with pytest.raises(PermissionDenied):
        backup_service.verify(actor_sin_permiso(), receipt.destination)


def test_last_verified_at_es_none_sin_respaldos(backup_service):
    assert backup_service.last_verified_at(SYSTEM_ACTOR) is None


def test_restore_to_trial_nunca_toca_la_base_activa(backup_service, tmp_path, db_path):
    destino = tmp_path / "respaldos"
    destino.mkdir()
    receipt = backup_service.create(SYSTEM_ACTOR, destino)

    ensayo_dir = tmp_path / "ensayo"
    ensayo_dir.mkdir()

    resultado = backup_service.restore_to_trial(SYSTEM_ACTOR, receipt.destination, ensayo_dir)

    assert resultado.target == ensayo_dir / "sistemashn-ensayo.db"
    assert resultado.target.exists()
    assert resultado.target != Path(db_path)
    # La base activa sigue intacta y no fue sobrescrita por la restauración.
    assert Path(db_path).exists()


def test_restore_to_trial_sin_permiso_falla(backup_service, tmp_path):
    destino = tmp_path / "respaldos"
    destino.mkdir()
    receipt = backup_service.create(SYSTEM_ACTOR, destino)
    ensayo_dir = tmp_path / "ensayo"
    ensayo_dir.mkdir()

    with pytest.raises(PermissionDenied):
        backup_service.restore_to_trial(actor_sin_permiso(), receipt.destination, ensayo_dir)


def test_restore_to_trial_destino_existente_falla(backup_service, tmp_path):
    destino = tmp_path / "respaldos"
    destino.mkdir()
    receipt = backup_service.create(SYSTEM_ACTOR, destino)
    ensayo_dir = tmp_path / "ensayo"
    ensayo_dir.mkdir()
    (ensayo_dir / "sistemashn-ensayo.db").write_bytes(b"ya existe")

    with pytest.raises(DestinationExistsError):
        backup_service.restore_to_trial(SYSTEM_ACTOR, receipt.destination, ensayo_dir)


def test_history_sin_permiso_falla(backup_service):
    with pytest.raises(PermissionDenied):
        backup_service.history(actor_sin_permiso())
