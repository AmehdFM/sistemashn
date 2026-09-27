"""Servicio de ajustes: datos del negocio, logo y valores clave/valor tipados (T1.5)."""

import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import ValidationError
from sistemashn.core.settings.models import Business, Setting
from sistemashn.core.settings.schemas import BusinessInput, BusinessView

BUSINESS_ID = 1
MAX_LOGO_BYTES = 2 * 1024 * 1024

# Firmas de bytes reconocidas (magic numbers) por extensión de destino.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpg"),
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def sniff_image_extension(data: bytes) -> str:
    """Determina la extensión (`png`/`jpg`) a partir de la firma de bytes del archivo.

    Lanza `ValidationError` si no es PNG ni JPG, sin importar el nombre del archivo.
    """
    for firma, extension in _SIGNATURES:
        if data.startswith(firma):
            return extension
    raise ValidationError("el logo debe ser una imagen PNG o JPG")


def save_logo(data_dir: Path, source: Path) -> str:
    """Valida y copia `source` a `data_dir/logo.<ext>`, reemplazando cualquier logo anterior.

    Retorna el nombre de archivo guardado (relativo a `data_dir`).
    """
    contenido = source.read_bytes()
    if len(contenido) > MAX_LOGO_BYTES:
        raise ValidationError(f"el logo no puede superar {MAX_LOGO_BYTES // (1024 * 1024)} MB")
    extension = sniff_image_extension(contenido)

    data_dir.mkdir(parents=True, exist_ok=True)
    for existente in data_dir.glob("logo.*"):
        existente.unlink()

    destino = data_dir / f"logo.{extension}"
    shutil.copyfile(source, destino)
    return destino.name


def _to_view(business: Business) -> BusinessView:
    return BusinessView(
        id=business.id,
        name=business.name,
        legal_name=business.legal_name,
        rtn=business.rtn,
        address=business.address,
        phone=business.phone,
        email=business.email,
        logo_path=business.logo_path,
        prices_include_isv=business.prices_include_isv,
        fiscal_enabled=business.fiscal_enabled,
        updated_at=business.updated_at,
    )


def apply_business_input(business: Business, data: BusinessInput, ahora: datetime) -> None:
    """Aplica `data` sobre `business` sin tocar `fiscal_enabled` ni `logo_path`."""
    business.name = data.name
    business.legal_name = data.legal_name
    business.rtn = data.rtn
    business.address = data.address
    business.phone = data.phone
    business.email = data.email
    business.prices_include_isv = data.prices_include_isv
    business.updated_at = ahora


class SettingsService:
    """Ajustes del negocio, logo y valores de configuración tipados con Pydantic."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime],
        data_dir: Path,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock
        self.data_dir = data_dir

    def get_business(self) -> BusinessView | None:
        """Sin verificación de permiso: la UI la necesita para mostrar nombre/logo siempre."""

        def _op(session: Session) -> BusinessView | None:
            business = session.get(Business, BUSINESS_ID)
            return _to_view(business) if business is not None else None

        return run_in_transaction(self.factory, _op, readonly=True)

    def update_business(self, actor: Actor, data: BusinessInput) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "core.ajustes.gestionar")
            business = session.get(Business, BUSINESS_ID)
            ahora = self.clock()

            antes = _to_view(business).model_dump(mode="json") if business is not None else None
            if business is None:
                business = Business(
                    id=BUSINESS_ID,
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
            session.flush()

            audit(
                session,
                actor,
                "core.ajustes.negocio_actualizado",
                entity_type="core_business",
                entity_id=str(BUSINESS_ID),
                summary="Datos del negocio actualizados",
                detail={"antes": antes, "despues": _to_view(business).model_dump(mode="json")},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def set_logo(self, actor: Actor, source: Path) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "core.ajustes.gestionar")
            business = session.get(Business, BUSINESS_ID)
            if business is None:
                raise ValidationError("no se puede fijar el logo sin datos de negocio")

            nombre_archivo = save_logo(self.data_dir, source)
            business.logo_path = nombre_archivo
            business.updated_at = self.clock()
            session.flush()

            audit(
                session,
                actor,
                "core.ajustes.logo_actualizado",
                entity_type="core_business",
                entity_id=str(BUSINESS_ID),
                summary="Logo del negocio actualizado",
                detail={"logo_path": nombre_archivo},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def get[T: BaseModel](self, key: str, model: type[T]) -> T | None:
        def _op(session: Session) -> str | None:
            fila = session.get(Setting, key)
            return fila.value_json if fila is not None else None

        value_json = run_in_transaction(self.factory, _op, readonly=True)
        return model.model_validate_json(value_json) if value_json is not None else None

    def set(self, actor: Actor, key: str, value: BaseModel) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "core.ajustes.gestionar")
            value_json = value.model_dump_json()
            fila = session.get(Setting, key)
            if fila is None:
                session.add(Setting(key=key, value_json=value_json))
            else:
                fila.value_json = value_json
            session.flush()

            audit(
                session,
                actor,
                "core.ajustes.valor_actualizado",
                entity_type="core_setting",
                entity_id=key,
                summary=f"Ajuste '{key}' actualizado",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)
