"""Composición del `AppContext`: base de datos, módulos, autorización y servicios."""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sistemashn import __version__
from sistemashn.comercial import composition as comercial_composition
from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.core.audit.service import AuditQueryService
from sistemashn.core.authorization.service import Authorizer, PermissionAdminService
from sistemashn.core.db import migrate
from sistemashn.core.db.base import Base
from sistemashn.core.db.engine import create_engine_for_path
from sistemashn.core.db.engine import data_dir as default_data_dir
from sistemashn.core.db.session import make_session_factory
from sistemashn.core.identity.recovery import RecoveryService
from sistemashn.core.identity.service import IdentityService
from sistemashn.core.licensing.fingerprint import machine_fingerprint
from sistemashn.core.licensing.keys import VENDOR_PUBLIC_KEYS
from sistemashn.core.licensing.service import LicenseService
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE
from sistemashn.core.settings.service import SettingsService
from sistemashn.core.setup.service import SetupService
from sistemashn.core.ui.app_context import AppContext
from sistemashn.repuestos import composition as repuestos_composition
from sistemashn.repuestos.module import REPUESTOS_MODULE

DB_FILENAME = "sistemashn.db"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _resolve_data_dir(vertical: str) -> Path:
    """`--data-dir` en `sys.argv` tiene prioridad sobre el valor por defecto del motor."""
    for indice, arg in enumerate(sys.argv):
        if arg == "--data-dir" and indice + 1 < len(sys.argv):
            return Path(sys.argv[indice + 1])
        if arg.startswith("--data-dir="):
            return Path(arg.split("=", 1)[1])
    return default_data_dir(vertical)


def build_context(
    data_dir: Path | None = None,
    *,
    vertical: str = "repuestos",
    clock: Callable[[], datetime] | None = None,
    fingerprint_fn: Callable[[], str] | None = None,
) -> AppContext:
    """Compone el `AppContext`: base de datos, módulos, autorización y servicios registrados.

    `data_dir` explícito tiene prioridad; si no se indica, se resuelve de `--data-dir` en
    `sys.argv`, la variable de entorno `SISTEMASHN_DATA_DIR` o la carpeta por defecto del
    motor (`sistemashn.core.db.engine.data_dir`).
    """
    reloj = clock or _utcnow
    carpeta = Path(data_dir) if data_dir is not None else _resolve_data_dir(vertical)
    carpeta.mkdir(parents=True, exist_ok=True)

    db_path = carpeta / DB_FILENAME
    migrate.upgrade(db_path)

    engine = create_engine_for_path(db_path)
    # TODO("fase 1 cierre: migración 0001_core"): retirar `create_all` cuando la cadena de
    # migraciones incluya todos los modelos del Core/Comercial/Repuestos.
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    registry = ModuleRegistry()
    registry.register(CORE_MODULE)
    registry.register(COMERCIAL_MODULE)
    registry.register(REPUESTOS_MODULE)
    registry.validate()

    authorizer = Authorizer(registry, reloj)

    huella = fingerprint_fn or machine_fingerprint
    license_service = LicenseService(
        factory, VENDOR_PUBLIC_KEYS, fingerprint_fn=huella, clock=reloj
    )
    setup_service = SetupService(factory, reloj, license_service, carpeta, vertical, __version__)
    instalacion = setup_service.ensure_installation()

    identity_service = IdentityService(factory, authorizer, reloj)
    recovery_service = RecoveryService(
        factory, reloj, VENDOR_PUBLIC_KEYS, lambda: instalacion.installation_id
    )
    permissions_service = PermissionAdminService(factory, authorizer, reloj)
    audit_service = AuditQueryService(factory, authorizer)
    settings_service = SettingsService(factory, authorizer, reloj, carpeta)

    ctx = AppContext(
        session_factory=factory,
        registry=registry,
        authorizer=authorizer,
        clock=reloj,
        data_dir=carpeta,
    )
    ctx.services["identity"] = identity_service
    ctx.services["recovery"] = recovery_service
    ctx.services["permissions"] = permissions_service
    ctx.services["audit"] = audit_service
    ctx.services["settings"] = settings_service
    ctx.services["setup"] = setup_service
    ctx.services["license"] = license_service
    comercial_composition.register_services(
        ctx,
        search_providers=repuestos_composition.search_providers(),
        excel_extensions=repuestos_composition.excel_extensions(),
    )
    repuestos_composition.register_services(ctx)

    negocio = settings_service.get_business()
    if negocio is not None:
        ctx.business_name = negocio.name
        if negocio.logo_path:
            ctx.logo_path = carpeta / negocio.logo_path

    return ctx
