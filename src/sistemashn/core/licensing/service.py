"""Servicio de licencia offline: código de solicitud, instalación y consulta (T1.4)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.licensing.fingerprint import machine_fingerprint
from sistemashn.core.licensing.license import (
    LicenseInfo,
    build_request_code,
    verify_license,
)
from sistemashn.core.licensing.models import InstalledLicense


def _default_clock() -> datetime:
    return datetime.now(UTC)


class LicenseService:
    """Genera códigos de solicitud, instala licencias firmadas y consulta la vigente."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        public_keys: dict[str, bytes],
        *,
        fingerprint_fn: Callable[[], str] = machine_fingerprint,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self._factory = factory
        self._public_keys = public_keys
        self._fingerprint_fn = fingerprint_fn
        self._clock = clock

    def request_code(self, installation_id: str, vertical: str, app_version: str) -> str:
        """Código `SHNREQ1...` con la huella actual, para pedirle licencia al vendedor."""
        return build_request_code(installation_id, vertical, self._fingerprint_fn(), app_version)

    def install(self, text: str, *, expected_vertical: str, installation_id: str) -> LicenseInfo:
        """Verifica `text` y la guarda, dejando el historial de licencias anteriores intacto.

        Lanza `LicenseError` si la licencia no es válida para esta instalación/máquina.
        """
        info = verify_license(
            text,
            expected_vertical=expected_vertical,
            installation_id=installation_id,
            fingerprint=self._fingerprint_fn(),
            public_keys=self._public_keys,
        )

        def _guardar(session: Session) -> None:
            session.add(
                InstalledLicense(
                    raw_text=info.raw_text,
                    license_id=info.license_id,
                    installed_at=self._clock(),
                )
            )

        run_in_transaction(self._factory, _guardar)
        return info

    def current(self, *, expected_vertical: str, installation_id: str) -> LicenseInfo | None:
        """Re-verifica la última licencia guardada contra la huella actual.

        Retorna `None` si no hay ninguna instalada. Si la huella de la máquina ya no
        coincide (cambio de hardware), lanza `LicenseError("maquina")`.
        """

        def _leer_ultima(session: Session) -> str | None:
            fila = (
                session.execute(
                    select(InstalledLicense).order_by(
                        InstalledLicense.installed_at.desc(), InstalledLicense.id.desc()
                    )
                )
                .scalars()
                .first()
            )
            return fila.raw_text if fila is not None else None

        raw_text = run_in_transaction(self._factory, _leer_ultima, readonly=True)
        if raw_text is None:
            return None

        return verify_license(
            raw_text,
            expected_vertical=expected_vertical,
            installation_id=installation_id,
            fingerprint=self._fingerprint_fn(),
            public_keys=self._public_keys,
        )
