"""Fixtures locales de las pruebas de cuentas por pagar/cobrar (plan T3.3)."""

import pytest

from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.credito.service import AccountService
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.models import UserPermission
from sistemashn.core.identity.models import User


@pytest.fixture
def account_service(session_factory, authorizer, clock) -> AccountService:
    return AccountService(session_factory, authorizer, clock=clock)


@pytest.fixture
def proveedor_id(party_service, admin_actor) -> int:
    return party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.NEGOCIO, name="Repuestos El Motor", is_supplier=True),
    )


@pytest.fixture
def cliente_id(party_service, admin_actor) -> int:
    return party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.PERSONA, name="Juan Pérez", is_customer=True),
    )


@pytest.fixture
def bodega_pagador_actor(session_factory, now) -> Actor:
    """Perfil bodega, más un override que le otorga `com.cxp.pagar` (no `com.cxc.cobrar`)."""
    with session_factory() as session:
        user = User(
            username="bodega_pagador",
            full_name="Usuario bodega_pagador",
            password_hash="hash",
            is_admin=False,
            is_active=True,
            profile_code="bodega",
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.flush()
        session.add(UserPermission(user_id=user.id, permission_code="com.cxp.pagar", granted=True))
        session.commit()
        user_id = user.id
    return Actor(user_id=user_id, username="bodega_pagador", is_admin=False, session_id="s-bp")
