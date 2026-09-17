from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.api.deps_audit import get_audit_context
from app.db.deps import get_db
from app.crud.crud_roles import (
    get_role_by_id,
    get_role_by_id_for_update,
    get_role_referencing_constraints,
    get_role_by_name,
    get_roles,
)
from app.schemas.audit_context import AuditContext
from app.schemas.bitacora import TipoActorBitacora
from app.services.audit_engine import AuditEngine, AuditRequirement
from app.services.audit_errors import AuditDisabledError, AuditEngineError, AuditTransactionError
from app.services import role_audit
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/roles", tags=["Roles"])


PROTECTED_ROLE_NAMES = {"ADMIN", "OPERADOR", "MANTENIMIENTO"}


def _get_admin_audit_context(request: Request, current_user=Depends(require_admin)) -> AuditContext:
    return get_audit_context(request)


def _audit_engine() -> AuditEngine:
    return AuditEngine()


def _require_actor(context: AuditContext) -> None:
    if context.actor.tipo is not TipoActorBitacora.USUARIO or (
        context.actor.usuario_id is None or context.request_id is None
    ):
        raise AuditTransactionError()


def _reject_protected_role(db: Session, context: AuditContext, role, action: str, code: str, detail: str) -> None:
    event_data = role_audit.role_event_data(action, role.id_rol, before=role_audit.snapshot_role(role))
    engine = _audit_engine()
    try:
        # Only a read/lock happened: release it without fabricating business failure.
        if db.new or db.dirty or db.deleted:
            raise AuditTransactionError()
        db.rollback()
        if engine.enabled:
            _require_actor(context)
            engine.record_rejected(context, functional_session=db, error_codigo=code, **event_data)
    except Exception as exc:
        raise HTTPException(500, "No fue posible registrar el rechazo de la operación de rol") from exc
    raise HTTPException(400, detail)


def _delete_failure_code(exc: IntegrityError, constraints) -> str | None:
    diagnostic = getattr(exc.orig, "diag", None)
    state = getattr(exc.orig, "sqlstate", None)
    if state == "23502" and (
        getattr(diagnostic, "schema_name", None), getattr(diagnostic, "table_name", None),
        getattr(diagnostic, "column_name", None),
    ) == ("public", "usuarios", "id_rol"):
        # The inspected ORM mapping can null this FK; no FALLIDO policy for it in 5.3.
        return None
    if state == "23503" and (
        getattr(diagnostic, "schema_name", None), getattr(diagnostic, "table_name", None),
        getattr(diagnostic, "constraint_name", None),
    ) in constraints:
        return "ROL_ELIMINACION_BLOQUEADA"
    return None


def _complete_role_mutation(db: Session, context: AuditContext, mutate, *, response=False, delete_event=None):
    try:
        operation = _audit_engine().operation(db, context, requirement=AuditRequirement.REQUIRED)
    except AuditDisabledError as exc:
        raise HTTPException(503, "La operación requiere auditoría habilitada") from exc
    except AuditEngineError as exc:
        raise HTTPException(500, "No fue posible completar la operación de rol") from exc
    constraints = frozenset()
    mutation_started = False
    try:
        with operation:
            _require_actor(operation.context)
            if delete_event is not None:
                constraints = get_role_referencing_constraints(db)
            mutation_started = True
            role = mutate(operation)
            prepared = RoleResponse.model_validate(role) if response else None
    except IntegrityError as exc:
        operation.rollback_business()
        if delete_event is not None:
            error_code = _delete_failure_code(exc, constraints) if mutation_started else None
            if error_code is not None:
                try:
                    operation.failure(exc, **delete_event, error_codigo=error_code)
                except AuditEngineError as audit_error:
                    raise HTTPException(500, "No fue posible completar la operación de rol") from audit_error
            # Preserve the historical 409 also for ORM NOT NULL and unknown integrity errors.
            raise HTTPException(409, "No se puede eliminar el rol porque tiene usuarios ligados") from exc
        raise HTTPException(500, "No fue posible completar la operación de rol") from exc
    except Exception as exc:
        operation.rollback_business()
        raise HTTPException(500, "No fue posible completar la operación de rol") from exc
    try:
        db.commit()
    except Exception as exc:
        # An uncertain COMMIT is not evidence of rollback: never emit FALLIDO here.
        db.close()
        raise HTTPException(500, "No fue posible confirmar la operación de rol") from exc
    return prepared


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_new_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    audit_context: AuditContext = Depends(_get_admin_audit_context),
):
    existing_role = get_role_by_name(db, role_in.nombre)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con ese nombre",
        )

    return _complete_role_mutation(
        db, audit_context, lambda operation: role_audit.create_role_with_audit(db, operation, role_in), response=True,
    )


@router.get("/", response_model=list[RoleResponse])
def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_roles(db, skip=skip, limit=limit)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    db_role = get_role_by_id(db, role_id)
    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )
    return db_role


@router.put("/{role_id}", response_model=RoleResponse)
def update_existing_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(get_db),
    audit_context: AuditContext = Depends(_get_admin_audit_context),
):
    db_role = get_role_by_id_for_update(db, role_id)
    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    current_role_name = (db_role.nombre or "").strip().upper()
    if current_role_name in PROTECTED_ROLE_NAMES and role_in.nombre is not None:
        new_role_name = role_in.nombre.strip().upper()
        if new_role_name != current_role_name:
            _reject_protected_role(
                db, audit_context, db_role, "ROL_ACTUALIZADO", "ROL_BASE_RENOMBRE_PROHIBIDO",
                f"No se puede renombrar el rol base {current_role_name}",
            )

    if role_in.nombre is not None:
        existing_role = get_role_by_name(db, role_in.nombre)
        if existing_role and existing_role.id_rol != role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro rol con ese nombre",
            )

    if not role_audit.has_role_changes(db_role, role_in):
        return RoleResponse.model_validate(db_role)
    return _complete_role_mutation(
        db, audit_context, lambda operation: role_audit.update_role_with_audit(db, operation, db_role, role_in), response=True,
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_role(
    role_id: int,
    db: Session = Depends(get_db),
    audit_context: AuditContext = Depends(_get_admin_audit_context),
):
    db_role = get_role_by_id_for_update(db, role_id)
    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    current_role_name = (db_role.nombre or "").strip().upper()
    if current_role_name in PROTECTED_ROLE_NAMES:
        _reject_protected_role(
            db, audit_context, db_role, "ROL_ELIMINADO", "ROL_BASE_ELIMINACION_PROHIBIDA",
            f"No se puede eliminar el rol base {current_role_name}",
        )

    event_data = role_audit.role_event_data("ROL_ELIMINADO", db_role.id_rol, before=role_audit.snapshot_role(db_role))
    _complete_role_mutation(
        db, audit_context, lambda operation: role_audit.delete_role_with_audit(db, operation, db_role, event_data),
        delete_event=event_data,
    )

    return None
