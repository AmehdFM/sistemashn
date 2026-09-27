"""Asistente de primer arranque: licencia, negocio, admin y códigos de recuperación (T1.5)."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import SYSTEM_ACTOR
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import ValidationError
from sistemashn.core.identity.models import User
from sistemashn.core.identity.passwords import hash_password
from sistemashn.core.identity.recovery import generate_codes
from sistemashn.core.identity.service import normalize_username
from sistemashn.core.licensing.service import LicenseService
from sistemashn.core.settings.models import Business
from sistemashn.core.settings.schemas import BusinessInput
from sistemashn.core.settings.service import apply_business_input, save_logo
from sistemashn.core.setup.models import Installation

INSTALLATION_ID_ROW = 1
_USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,32}$")


class SetupStep(StrEnum):
    LICENSE = "license"
    BUSINESS = "business"
    ADMIN = "admin"
    RECOVERY = "recovery"
    DONE = "done"


_ORDER = (
    SetupStep.LICENSE,
    SetupStep.BUSINESS,
    SetupStep.ADMIN,
    SetupStep.RECOVERY,
    SetupStep.DONE,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class InstallationView:
    installation_id: str
    vertical: str
    setup_step: SetupStep
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class SetupState:
    step: SetupStep
    installation_id: str
    request_code: str | None = None


def _to_view(installation: Installation) -> InstallationView:
    return InstallationView(
        installation_id=installation.installation_id,
        vertical=installation.vertical,
        setup_step=SetupStep(installation.setup_step),
        created_at=installation.created_at,
        completed_at=installation.completed_at,
    )


class SetupService:
    """Guía el primer arranque: licencia, negocio, admin y códigos de recuperación."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        clock: Callable[[], datetime],
        license_service: LicenseService,
        data_dir: Path,
        vertical: str,
        app_version: str,
    ) -> None:
        self.factory = factory
        self.clock = clock
        self.license_service = license_service
        self.data_dir = data_dir
        self.vertical = vertical
        self.app_version = app_version

    def ensure_installation(self) -> InstallationView:
        """Crea la fila de instalación si no existe; llamar varias veces no tiene efecto."""

        def _op(session: Session) -> InstallationView:
            installation = session.get(Installation, INSTALLATION_ID_ROW)
            if installation is None:
                installation = Installation(
                    id=INSTALLATION_ID_ROW,
                    installation_id=str(uuid4()),
                    vertical=self.vertical,
                    setup_step=SetupStep.LICENSE.value,
                    created_at=self.clock(),
                    completed_at=None,
                )
                session.add(installation)
                session.flush()
            return _to_view(installation)

        return run_in_transaction(self.factory, _op)

    def _get_installation(self, session: Session) -> Installation:
        installation = session.get(Installation, INSTALLATION_ID_ROW)
        if installation is None:
            raise ValidationError("la instalación aún no se inicializó")
        return installation

    def _require_step(self, installation: Installation, expected: SetupStep) -> None:
        if installation.setup_step != expected.value:
            raise ValidationError("paso de configuración inválido")

    def _advance(self, installation: Installation) -> None:
        actual = SetupStep(installation.setup_step)
        siguiente = _ORDER[_ORDER.index(actual) + 1]
        installation.setup_step = siguiente.value

    def state(self) -> SetupState:
        def _op(session: Session) -> SetupState:
            installation = self._get_installation(session)
            paso = SetupStep(installation.setup_step)
            request_code = None
            if paso == SetupStep.LICENSE:
                request_code = self.license_service.request_code(
                    installation.installation_id, installation.vertical, self.app_version
                )
            return SetupState(
                step=paso, installation_id=installation.installation_id, request_code=request_code
            )

        return run_in_transaction(self.factory, _op, readonly=True)

    def submit_license(self, text: str) -> None:
        """Instala la licencia y avanza a `business`. Propaga `LicenseError` si no es válida."""

        def _leer(session: Session) -> Installation:
            installation = self._get_installation(session)
            self._require_step(installation, SetupStep.LICENSE)
            return installation

        installation = run_in_transaction(self.factory, _leer, readonly=True)

        # `LicenseError` se propaga tal cual: el paso no avanza si la licencia no es válida.
        self.license_service.install(
            text,
            expected_vertical=installation.vertical,
            installation_id=installation.installation_id,
        )

        def _avanzar(session: Session) -> None:
            installation = self._get_installation(session)
            self._require_step(installation, SetupStep.LICENSE)
            self._advance(installation)
            session.flush()
            audit(
                session,
                SYSTEM_ACTOR,
                "core.setup.licencia_instalada",
                entity_type="core_installation",
                summary="Licencia instalada durante el primer arranque",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _avanzar)

    def submit_business(self, data: BusinessInput, logo: Path | None = None) -> None:
        """Crea/actualiza los datos del negocio (y el logo opcional) y avanza a `admin`."""

        def _op(session: Session) -> None:
            installation = self._get_installation(session)
            self._require_step(installation, SetupStep.BUSINESS)

            ahora = self.clock()
            business = session.get(Business, 1)
            if business is None:
                business = Business(
                    id=1,
                    logo_path=None,
                    fiscal_enabled=False,
                    updated_at=ahora,
                    name=data.name,
                    legal_name=data.legal_name,
                    rtn=data.rtn,
                    address=data.address,
                    phone=data.phone,
                    email=data.email,
                    prices_include_isv=data.prices_include_isv,
                )
                session.add(business)
            else:
                apply_business_input(business, data, ahora)

            if logo is not None:
                business.logo_path = save_logo(self.data_dir, logo)

            self._advance(installation)
            session.flush()

            audit(
                session,
                SYSTEM_ACTOR,
                "core.setup.negocio_registrado",
                entity_type="core_business",
                summary="Datos del negocio registrados durante el primer arranque",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def create_admin(self, username: str, full_name: str, password: str) -> list[str]:
        """Crea el administrador y sus códigos de recuperación en una sola transacción.

        Los códigos se devuelven en claro únicamente aquí: solo se guardan sus hashes.
        """

        def _op(session: Session) -> list[str]:
            installation = self._get_installation(session)
            self._require_step(installation, SetupStep.ADMIN)

            normalizado = normalize_username(username)
            if not _USERNAME_RE.match(normalizado):
                raise ValidationError("nombre de usuario inválido: 3-32 caracteres [a-z0-9._-]")

            password_hash = hash_password(password)  # valida la política; ValidationError si débil

            ahora = self.clock()
            admin = User(
                username=normalizado,
                full_name=full_name,
                password_hash=password_hash,
                is_admin=True,
                is_active=True,
                profile_code="administrador",
                permissions_version=1,
                failed_attempts=0,
                locked_until=None,
                must_change_password=False,
                created_at=ahora,
                updated_at=ahora,
            )
            session.add(admin)
            session.flush()

            codigos = generate_codes(session, clock=self.clock)
            self._advance(installation)
            session.flush()

            audit(
                session,
                SYSTEM_ACTOR,
                "core.setup.admin_creado",
                entity_type="core_user",
                entity_id=str(admin.id),
                summary=f"Administrador '{normalizado}' creado durante el primer arranque",
                clock=self.clock,
            )
            return codigos

        return run_in_transaction(self.factory, _op)

    def regenerate_recovery_codes_during_setup(self) -> list[str]:
        """Regenera los códigos de recuperación; solo válido mientras el paso es `recovery`."""

        def _op(session: Session) -> list[str]:
            installation = self._get_installation(session)
            self._require_step(installation, SetupStep.RECOVERY)

            codigos = generate_codes(session, clock=self.clock)
            session.flush()
            audit(
                session,
                SYSTEM_ACTOR,
                "core.setup.codigos_regenerados",
                summary="Códigos de recuperación regenerados durante el primer arranque",
                clock=self.clock,
            )
            return codigos

        return run_in_transaction(self.factory, _op)

    def confirm_recovery_codes_saved(self) -> None:
        def _op(session: Session) -> None:
            installation = self._get_installation(session)
            self._require_step(installation, SetupStep.RECOVERY)
            self._advance(installation)
            installation.completed_at = self.clock()
            session.flush()

            audit(
                session,
                SYSTEM_ACTOR,
                "core.setup.completado",
                entity_type="core_installation",
                summary="Primer arranque completado",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)
