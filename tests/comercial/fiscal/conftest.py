"""Fixtures locales de las pruebas de facturación fiscal (plan T4.5)."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session, sessionmaker

from sistemashn.comercial.fiscal.service import FiscalService
from sistemashn.core.settings.models import Business


@pytest.fixture
def fiscal_service(session_factory, authorizer, clock) -> FiscalService:
    return FiscalService(session_factory, authorizer, clock=clock)


def set_business_fiscal(
    session_factory: sessionmaker[Session], now: datetime, *, fiscal_enabled: bool
) -> None:
    """Crea o actualiza la fila única `core_business` (`id=1`) con `fiscal_enabled` dado."""
    with session_factory() as session:
        business = session.get(Business, 1)
        if business is None:
            business = Business(
                id=1,
                name="Repuestos de prueba",
                legal_name="Repuestos de prueba S. de R.L.",
                rtn=None,
                address="Tegucigalpa",
                phone="0000-0000",
                email="pruebas@example.com",
                logo_path=None,
                prices_include_isv=True,
                fiscal_enabled=fiscal_enabled,
                updated_at=now,
            )
            session.add(business)
        else:
            business.fiscal_enabled = fiscal_enabled
            business.updated_at = now
        session.commit()
