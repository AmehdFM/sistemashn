"""Servicio de marcas y modelos de vehículo (plan T2.4)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.repuestos.vehiculos.models import VehicleMake, VehicleModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class VehicleMakeView:
    id: int
    name: str


@dataclass(frozen=True)
class VehicleModelView:
    id: int
    make_id: int
    name: str


class VehicleService:
    """Alta y consulta de marcas y modelos de vehículo."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    def create_make(self, actor: Actor, name: str) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "rep.vehiculos.gestionar")
            nombre = name.strip()
            if not nombre:
                raise ValidationError("el nombre de la marca no puede estar vacío")
            existente = session.scalar(
                select(VehicleMake).where(func.lower(VehicleMake.name) == nombre.lower())
            )
            if existente is not None:
                raise ValidationError(f"la marca '{nombre}' ya existe")
            marca = VehicleMake(name=nombre)
            session.add(marca)
            session.flush()
            return marca.id

        return run_in_transaction(self.factory, _op)

    def list_makes(self, actor: Actor) -> list[VehicleMakeView]:
        def _op(session: Session) -> list[VehicleMakeView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            filas = session.scalars(select(VehicleMake).order_by(VehicleMake.name)).all()
            return [VehicleMakeView(id=m.id, name=m.name) for m in filas]

        return run_in_transaction(self.factory, _op, readonly=True)

    def create_model(self, actor: Actor, make_id: int, name: str) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "rep.vehiculos.gestionar")
            marca = session.get(VehicleMake, make_id)
            if marca is None:
                raise NotFound(f"marca {make_id} no existe")
            nombre = name.strip()
            if not nombre:
                raise ValidationError("el nombre del modelo no puede estar vacío")
            existente = session.scalar(
                select(VehicleModel).where(
                    VehicleModel.make_id == make_id,
                    func.lower(VehicleModel.name) == nombre.lower(),
                )
            )
            if existente is not None:
                raise ValidationError(f"el modelo '{nombre}' ya existe para esa marca")
            modelo = VehicleModel(make_id=make_id, name=nombre)
            session.add(modelo)
            session.flush()
            return modelo.id

        return run_in_transaction(self.factory, _op)

    def list_models(self, actor: Actor, make_id: int) -> list[VehicleModelView]:
        def _op(session: Session) -> list[VehicleModelView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            filas = session.scalars(
                select(VehicleModel)
                .where(VehicleModel.make_id == make_id)
                .order_by(VehicleModel.name)
            ).all()
            return [VehicleModelView(id=m.id, make_id=m.make_id, name=m.name) for m in filas]

        return run_in_transaction(self.factory, _op, readonly=True)
