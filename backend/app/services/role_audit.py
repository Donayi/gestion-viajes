"""Explicit role snapshots; transaction ownership stays in the route."""

from sqlalchemy.orm import Session

from app.crud import crud_roles
from app.models.models import Rol
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.audit_engine import AuditedOperation


AUDIT_FIELDS = ("nombre", "descripcion")


def snapshot_role(role: Rol) -> dict[str, object]:
    return {"nombre": role.nombre, "descripcion": role.descripcion}


def has_role_changes(role: Rol, update: RoleUpdate) -> bool:
    return any(
        getattr(role, field) != getattr(update, field)
        for field in AUDIT_FIELDS if field in update.model_fields_set
    )


def diff_role_snapshots(before: dict, after: dict) -> tuple[dict, dict]:
    changed = [field for field in AUDIT_FIELDS if before[field] != after[field]]
    return ({field: before[field] for field in changed}, {field: after[field] for field in changed})


def role_event_data(action: str, role_id: int, *, before=None, after=None) -> dict:
    return {
        "categoria": "SEGURIDAD", "modulo": "ROLES", "accion": action,
        "entidad_tipo": "ROL", "entidad_id": str(role_id),
        "valores_anteriores": before, "valores_posteriores": after,
    }


def create_role_with_audit(db: Session, operation: AuditedOperation, role_in: RoleCreate) -> Rol:
    role = crud_roles.create_role(db, role_in)
    operation.success(**role_event_data("ROL_CREADO", role.id_rol, after=snapshot_role(role)))
    return role


def update_role_with_audit(db: Session, operation: AuditedOperation, role: Rol, update: RoleUpdate) -> Rol:
    before = snapshot_role(role)
    role = crud_roles.update_role(db, role, update)
    previous, following = diff_role_snapshots(before, snapshot_role(role))
    operation.success(**role_event_data("ROL_ACTUALIZADO", role.id_rol, before=previous, after=following))
    return role


def delete_role_with_audit(db: Session, operation: AuditedOperation, role: Rol, event_data: dict) -> None:
    crud_roles.delete_role(db, role)
    operation.success(**event_data)
