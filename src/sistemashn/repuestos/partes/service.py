"""Servicio de partes: datos de repuesto, equivalencias y compatibilidad (plan T2.4)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.models import Product
from sistemashn.core.audit.service import audit
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.pagination import Page, normalize_page
from sistemashn.repuestos.partes.models import EquivalenceGroup, Part
from sistemashn.repuestos.partes.search import normalize_part_number
from sistemashn.repuestos.vehiculos.models import Compatibility, VehicleModel

_ORIGENES_VALIDOS = ("original", "generico")
_ANIO_MINIMO = 1950
_ANIO_MAXIMO = 2100


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class PartView:
    product_id: int
    part_number: str
    manufacturer: str | None
    origin: str
    equivalence_group_id: int | None


@dataclass(frozen=True)
class ProductRef:
    id: int
    code: str
    name: str


@dataclass(frozen=True)
class CompatibilityView:
    id: int
    product_id: int
    model_id: int
    year_from: int
    year_to: int


def _part_to_view(part: Part) -> PartView:
    return PartView(
        product_id=part.product_id,
        part_number=part.part_number,
        manufacturer=part.manufacturer,
        origin=part.origin,
        equivalence_group_id=part.equivalence_group_id,
    )


def _compat_to_view(compat: Compatibility) -> CompatibilityView:
    return CompatibilityView(
        id=compat.id,
        product_id=compat.product_id,
        model_id=compat.model_id,
        year_from=compat.year_from,
        year_to=compat.year_to,
    )


def _product_to_ref(product: Product) -> ProductRef:
    return ProductRef(id=product.id, code=product.code, name=product.name)


class PartService:
    """Alta de datos de repuesto, equivalencias y compatibilidad con vehículos."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    # -- Datos de la parte --------------------------------------------------

    def set_part_info(
        self,
        actor: Actor,
        product_id: int,
        part_number: str,
        manufacturer: str | None,
        origin: str,
    ) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "rep.partes.gestionar")
            self._requerir_producto(session, product_id)

            numero = part_number.strip()
            if not numero:
                raise ValidationError("el número de parte no puede estar vacío")
            if origin not in _ORIGENES_VALIDOS:
                raise ValidationError(f"origen inválido: {origin!r}")

            part = session.get(Part, product_id)
            if part is None:
                part = Part(
                    product_id=product_id,
                    part_number=numero,
                    part_number_search=normalize_part_number(numero),
                    manufacturer=manufacturer,
                    origin=origin,
                )
                session.add(part)
            else:
                part.part_number = numero
                part.part_number_search = normalize_part_number(numero)
                part.manufacturer = manufacturer
                part.origin = origin
            session.flush()

            audit(
                session,
                actor,
                "rep.parte.actualizada",
                entity_type="rep_part",
                entity_id=str(product_id),
                summary=f"Datos de parte '{numero}' actualizados",
                detail={"part_number": numero, "manufacturer": manufacturer, "origin": origin},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def get_part(self, actor: Actor, product_id: int) -> PartView:
        def _op(session: Session) -> PartView:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            part = session.get(Part, product_id)
            if part is None:
                raise NotFound(f"el producto {product_id} no tiene datos de parte")
            return _part_to_view(part)

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Equivalencias --------------------------------------------------

    def link_equivalent(self, actor: Actor, product_id_a: int, product_id_b: int) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "rep.partes.gestionar")
            parte_a = self._requerir_parte(session, product_id_a)
            parte_b = self._requerir_parte(session, product_id_b)

            if (
                parte_a.equivalence_group_id is not None
                and parte_a.equivalence_group_id == parte_b.equivalence_group_id
            ):
                return  # ya son equivalentes: idempotente

            if parte_a.equivalence_group_id is None and parte_b.equivalence_group_id is None:
                grupo = EquivalenceGroup(created_at=self.clock())
                session.add(grupo)
                session.flush()
                parte_a.equivalence_group_id = grupo.id
                parte_b.equivalence_group_id = grupo.id
            elif parte_a.equivalence_group_id is None:
                parte_a.equivalence_group_id = parte_b.equivalence_group_id
            elif parte_b.equivalence_group_id is None:
                parte_b.equivalence_group_id = parte_a.equivalence_group_id
            else:
                grupo_menor = min(parte_a.equivalence_group_id, parte_b.equivalence_group_id)
                grupo_mayor = max(parte_a.equivalence_group_id, parte_b.equivalence_group_id)
                miembros = session.scalars(
                    select(Part).where(Part.equivalence_group_id == grupo_mayor)
                ).all()
                for miembro in miembros:
                    miembro.equivalence_group_id = grupo_menor
                grupo_vacio = session.get(EquivalenceGroup, grupo_mayor)
                if grupo_vacio is not None:
                    session.delete(grupo_vacio)
            session.flush()

            audit(
                session,
                actor,
                "rep.equivalencia.vinculada",
                entity_type="rep_part",
                entity_id=str(product_id_a),
                summary=f"Partes {product_id_a} y {product_id_b} vinculadas como equivalentes",
                detail={"product_id_a": product_id_a, "product_id_b": product_id_b},
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def unlink(self, actor: Actor, product_id: int) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "rep.partes.gestionar")
            part = self._requerir_parte(session, product_id)
            grupo_id = part.equivalence_group_id
            if grupo_id is None:
                return  # no pertenece a ningún grupo: nada que hacer

            part.equivalence_group_id = None
            session.flush()

            restantes = session.scalars(
                select(Part).where(Part.equivalence_group_id == grupo_id)
            ).all()
            if len(restantes) <= 1:
                for restante in restantes:
                    restante.equivalence_group_id = None
                grupo = session.get(EquivalenceGroup, grupo_id)
                if grupo is not None:
                    session.delete(grupo)
                session.flush()

            audit(
                session,
                actor,
                "rep.equivalencia.desvinculada",
                entity_type="rep_part",
                entity_id=str(product_id),
                summary=f"Parte {product_id} desvinculada de su grupo de equivalencia",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def equivalents(self, actor: Actor, product_id: int) -> list[ProductRef]:
        def _op(session: Session) -> list[ProductRef]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            part = session.get(Part, product_id)
            if part is None or part.equivalence_group_id is None:
                return []

            filas = session.scalars(
                select(Product)
                .join(Part, Part.product_id == Product.id)
                .where(
                    Part.equivalence_group_id == part.equivalence_group_id,
                    Product.id != product_id,
                    Product.active.is_(True),
                )
            ).all()
            return [_product_to_ref(p) for p in filas]

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Compatibilidad --------------------------------------------------

    def add_compatibility(
        self, actor: Actor, product_id: int, model_id: int, year_from: int, year_to: int
    ) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "rep.partes.gestionar")
            self._requerir_producto(session, product_id)
            modelo = session.get(VehicleModel, model_id)
            if modelo is None:
                raise NotFound(f"modelo de vehículo {model_id} no existe")

            if year_from > year_to:
                raise ValidationError("el año inicial no puede ser mayor al año final")
            if not (_ANIO_MINIMO <= year_from <= _ANIO_MAXIMO):
                raise ValidationError(f"año inicial fuera de rango ({_ANIO_MINIMO}-{_ANIO_MAXIMO})")
            if not (_ANIO_MINIMO <= year_to <= _ANIO_MAXIMO):
                raise ValidationError(f"año final fuera de rango ({_ANIO_MINIMO}-{_ANIO_MAXIMO})")

            compat = Compatibility(
                product_id=product_id, model_id=model_id, year_from=year_from, year_to=year_to
            )
            session.add(compat)
            session.flush()

            audit(
                session,
                actor,
                "rep.compatibilidad.agregada",
                entity_type="rep_compatibility",
                entity_id=str(compat.id),
                summary=f"Compatibilidad agregada al producto {product_id}",
                detail={
                    "product_id": product_id,
                    "model_id": model_id,
                    "year_from": year_from,
                    "year_to": year_to,
                },
                clock=self.clock,
            )
            return compat.id

        return run_in_transaction(self.factory, _op)

    def remove_compatibility(self, actor: Actor, compatibility_id: int) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "rep.partes.gestionar")
            compat = session.get(Compatibility, compatibility_id)
            if compat is None:
                raise NotFound(f"compatibilidad {compatibility_id} no existe")
            session.delete(compat)
            session.flush()

            audit(
                session,
                actor,
                "rep.compatibilidad.eliminada",
                entity_type="rep_compatibility",
                entity_id=str(compatibility_id),
                summary=f"Compatibilidad {compatibility_id} eliminada",
                clock=self.clock,
            )

        run_in_transaction(self.factory, _op)

    def compatibilities(self, actor: Actor, product_id: int) -> list[CompatibilityView]:
        def _op(session: Session) -> list[CompatibilityView]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            filas = session.scalars(
                select(Compatibility).where(Compatibility.product_id == product_id)
            ).all()
            return [_compat_to_view(c) for c in filas]

        return run_in_transaction(self.factory, _op, readonly=True)

    def compatible_products(
        self, actor: Actor, model_id: int, year: int, page: int = 1, page_size: int = 50
    ) -> Page[ProductRef]:
        def _op(session: Session) -> Page[ProductRef]:
            self.authorizer.require(session, actor, "com.catalogo.ver")
            page_num, size, offset = normalize_page(page, page_size)

            base = (
                select(Product.id, Product.code, Product.name)
                .join(Compatibility, Compatibility.product_id == Product.id)
                .where(
                    Compatibility.model_id == model_id,
                    Compatibility.year_from <= year,
                    Compatibility.year_to >= year,
                    Product.active.is_(True),
                )
                .distinct()
            )
            total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
            filas = session.execute(base.order_by(Product.name).offset(offset).limit(size)).all()
            items = [ProductRef(id=fila.id, code=fila.code, name=fila.name) for fila in filas]
            return Page(items=items, total=total, page=page_num, page_size=size)

        return run_in_transaction(self.factory, _op, readonly=True)

    # -- Internos --------------------------------------------------

    def _requerir_producto(self, session: Session, product_id: int) -> Product:
        product = session.get(Product, product_id)
        if product is None:
            raise NotFound(f"producto {product_id} no existe")
        return product

    def _requerir_parte(self, session: Session, product_id: int) -> Part:
        part = session.get(Part, product_id)
        if part is None:
            raise ValidationError(f"el producto {product_id} no tiene datos de parte")
        return part
