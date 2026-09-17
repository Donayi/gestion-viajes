from fastapi import Request

from app.schemas.audit_context import AuditContext
from app.services.audit_context import get_audit_state, refresh_audit_route


def get_audit_context(request: Request) -> AuditContext:
    state = get_audit_state(request.scope)
    if state is None:
        raise RuntimeError("El middleware de contexto de auditoría no está instalado")
    refresh_audit_route(request.scope, state)
    return state.context
