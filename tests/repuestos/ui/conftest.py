"""Fixtures de las pruebas de UI de Repuestos: `AppContext` construido con `build_context`."""

from datetime import UTC, datetime

import pytest

from sistemashn.app.bootstrap import build_context
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.identity.models import User
from sistemashn.core.identity.passwords import hash_password
from sistemashn.core.ui.app_context import AppContext

FIXED_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def _clock() -> datetime:
    return FIXED_NOW


@pytest.fixture
def ctx(tmp_path) -> AppContext:
    return build_context(
        tmp_path, vertical="repuestos", clock=_clock, fingerprint_fn=lambda: "x" * 64
    )


@pytest.fixture
def admin_actor(ctx: AppContext) -> Actor:
    with ctx.session_factory() as session:
        user = User(
            username="admin",
            full_name="Administrador",
            password_hash=hash_password("clave-de-prueba-1"),
            is_admin=True,
            is_active=True,
            profile_code=None,
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=FIXED_NOW,
            updated_at=FIXED_NOW,
        )
        session.add(user)
        session.commit()
        user_id = user.id
    return Actor(user_id=user_id, username="admin", is_admin=True, session_id="s-admin")


@pytest.fixture
def ctx_admin(ctx: AppContext, admin_actor: Actor) -> AppContext:
    ctx.actor = admin_actor
    return ctx
