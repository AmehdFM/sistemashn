"""Constructores de las pantallas del Core, indexados por ruta de `CORE_MODULE`."""

from sistemashn.core.ui.router import ScreenBuilder
from sistemashn.core.ui.views.audit_view import build_audit_view
from sistemashn.core.ui.views.backups_view import build_backups_view
from sistemashn.core.ui.views.business_view import build_business_view
from sistemashn.core.ui.views.license_view import build_license_view
from sistemashn.core.ui.views.operation_settings_view import build_operation_settings_view
from sistemashn.core.ui.views.users_view import build_users_view

CORE_SCREEN_BUILDERS: dict[str, ScreenBuilder] = {
    "/usuarios": build_users_view,
    "/auditoria": build_audit_view,
    "/ajustes": build_business_view,
    "/ajustes/operacion": build_operation_settings_view,
    "/respaldos": build_backups_view,
    "/licencia": build_license_view,
}
