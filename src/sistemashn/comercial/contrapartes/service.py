"""Servicio de contrapartes: alta con deduplicación asistida, roles y búsqueda (plan T3.1)."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.catalogo.search import normalize_search
from sistemashn.comercial.contrapartes.errors import PartyRef, PossibleDuplicate
from sistemashn.comercial.contrapartes.models import Party
from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind, PartyView
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.db.text import LIKE_ESCAPE, escape_like
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound
from sistemashn.core.pagination import Page, normalize_page


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _to_view(party: Party) -> PartyView:
    return PartyView(
        id=party.id,
        kind=PartyKind(party.kind),
        name=party.name,
        rtn=party.rtn,
        phone=party.phone,
        email=party.email,
        address=party.address,
        is_supplier=party.is_supplier,
        is_customer=party.is_customer,
        active=party.active,
        notes=party.notes,
        created_at=party.created_at,
        updated_at=party.updated_at,
    )


class PartyService:
    """Alta, edición, roles y búsqueda de contrapartes (proveedores y/o clientes)."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        authorizer: Authorizer,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.factory = factory
        self.authorizer = authorizer
        self.clock = clock

    def find_duplicates(
        self,
        session: Session,
        name: str,
        rtn: str | None,
        *,
        exclude_id: int | None = None,
    ) -> list[PartyRef]:
        """Contrapartes con el mismo RTN o el mismo nombre normalizado."""
        condiciones = [Party.name_search == normalize_search(name)]
        if rtn is not None:
            condiciones.append(Party.rtn == rtn)
        stmt = select(Party).where(or_(*condiciones))
        if exclude_id is not None:
            stmt = stmt.where(Party.id != exclude_id)
        candidatos = session.scalars(stmt).all()
        return [PartyRef(id=p.id, name=p.name, rtn=p.rtn) for p in candidatos]

    def create(self, actor: Actor, data: PartyInput, *, allow_duplicate: bool = False) -> int:
        def _op(session: Session) -> int:
            self.authorizer.require(session, actor, "com.contrapartes.gestionar")
            if not allow_duplicate:
                duplicados = self.find_duplicates(session, data.name, data.rtn)
                if duplicados:
                    raise PossibleDuplicate(duplicados)

            ahora = self.clock()
            party = Party(
                kind=data.kind.value,
                name=data.name,
                name_search=normalize_search(data.name),
                rtn=data.rtn,
                phone=data.phone,
                email=data.email,
                address=data.address,
                is_supplier=data.is_supplier,
                is_customer=data.is_customer,
                active=True,
                notes=data.notes,
                created_at=ahora,
                updated_at=ahora,
            )
            session.add(party)
            session.flush()
            return party.id

        return run_in_transaction(self.factory, _op)

    def update(
        self,
        actor: Actor,
        party_id: int,
        data: PartyInput,
        *,
        allow_duplicate: bool = False,
    ) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.contrapartes.gestionar")
            party = session.get(Party, party_id)
            if party is None:
                raise NotFound(f"contraparte {party_id} no existe")

            if not allow_duplicate:
                duplicados = self.find_duplicates(session, data.name, data.rtn, exclude_id=party_id)
                if duplicados:
                    raise PossibleDuplicate(duplicados)

            party.kind = data.kind.value
            party.name = data.name
            party.name_search = normalize_search(data.name)
            party.rtn = data.rtn
            party.phone = data.phone
            party.email = data.email
            party.address = data.address
            party.is_supplier = data.is_supplier
            party.is_customer = data.is_customer
            party.notes = data.notes
            party.updated_at = self.clock()
            session.flush()

        run_in_transaction(self.factory, _op)

    def set_roles(self, actor: Actor, party_id: int, *, supplier: bool, customer: bool) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.contrapartes.gestionar")
            party = session.get(Party, party_id)
            if party is None:
                raise NotFound(f"contraparte {party_id} no existe")
            party.is_supplier = supplier
            party.is_customer = customer
            party.updated_at = self.clock()
            session.flush()

        run_in_transaction(self.factory, _op)

    def set_active(self, actor: Actor, party_id: int, active: bool) -> None:
        def _op(session: Session) -> None:
            self.authorizer.require(session, actor, "com.contrapartes.gestionar")
            party = session.get(Party, party_id)
            if party is None:
                raise NotFound(f"contraparte {party_id} no existe")
            party.active = active
            party.updated_at = self.clock()
            session.flush()

        run_in_transaction(self.factory, _op)

    def get(self, actor: Actor, party_id: int) -> PartyView:
        def _op(session: Session) -> PartyView:
            self.authorizer.require(session, actor, "com.contrapartes.ver")
            party = session.get(Party, party_id)
            if party is None:
                raise NotFound(f"contraparte {party_id} no existe")
            return _to_view(party)

        return run_in_transaction(self.factory, _op, readonly=True)

    def search(
        self,
        actor: Actor,
        text: str = "",
        *,
        role: str | None = None,
        page: int = 1,
        page_size: int = 50,
        include_inactive: bool = False,
    ) -> Page[PartyView]:
        """Busca por nombre (sin acentos) o RTN. `role` filtra por 'supplier' o 'customer'."""

        def _op(session: Session) -> Page[PartyView]:
            self.authorizer.require(session, actor, "com.contrapartes.ver")
            page_num, size, offset = normalize_page(page, page_size)
            texto = text.strip()

            condiciones = []
            if texto:
                texto_normalizado = normalize_search(texto)
                condiciones.append(
                    or_(
                        Party.name_search.like(
                            f"%{escape_like(texto_normalizado)}%", escape=LIKE_ESCAPE
                        ),
                        Party.rtn.like(f"%{escape_like(texto)}%", escape=LIKE_ESCAPE),
                    )
                )
            if role == "supplier":
                condiciones.append(Party.is_supplier.is_(True))
            elif role == "customer":
                condiciones.append(Party.is_customer.is_(True))

            stmt = select(Party)
            if condiciones:
                stmt = stmt.where(and_(*condiciones))
            if not include_inactive:
                stmt = stmt.where(Party.active.is_(True))

            todos = sorted(session.scalars(stmt).all(), key=lambda p: p.name_search)
            total = len(todos)
            pagina = todos[offset : offset + size]

            return Page(
                items=[_to_view(p) for p in pagina], total=total, page=page_num, page_size=size
            )

        return run_in_transaction(self.factory, _op, readonly=True)
