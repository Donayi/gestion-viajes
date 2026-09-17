from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.api.deps_audit import get_audit_context
from app.db.deps import get_db
from app.crud.crud_usuarios import (
    get_user_by_id,
    get_user_by_id_for_update,
    get_user_referencing_constraints,
    get_user_by_username,
    get_users,
    role_exists,
)
from app.schemas.audit_context import AuditContext
from app.schemas.bitacora import TipoActorBitacora
from app.services.audit_engine import AuditEngine, AuditRequirement
from app.services.audit_errors import AuditDisabledError, AuditEngineError, AuditTransactionError
from app.services import user_audit
from app.schemas.user import UserAdminUpdate, UserCreate, UserPasswordUpdate, UserResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _get_admin_audit_context(request: Request, current_user=Depends(require_admin)) -> AuditContext:
    return get_audit_context(request)


def _audit_engine():
    return AuditEngine()


def _prepare_user_response(db, user):
    required = set(UserResponse.model_fields)
    missing = required.intersection(inspect(user).unloaded)
    if missing:
        db.refresh(user, attribute_names=sorted(missing))
    return UserResponse.model_validate(user)


def _recognized_delete_fk(exc, known_constraints):
    diagnostic = getattr(exc.orig, "diag", None)
    return getattr(exc.orig, "sqlstate", None) == "23503" and (
        getattr(diagnostic, "schema_name", None), getattr(diagnostic, "table_name", None),
        getattr(diagnostic, "constraint_name", None),
    ) in known_constraints


def _complete_user_mutation(db, context, mutate, *, response=False, delete_event=None):
    """Only these four user mutations: preparation and commit have separate boundaries."""
    try:
        operation = _audit_engine().operation(db, context, requirement=AuditRequirement.REQUIRED)
    except AuditDisabledError as exc:
        raise HTTPException(503, "La operación requiere auditoría habilitada") from exc
    except AuditEngineError as exc:
        raise HTTPException(500, "No fue posible completar la operación de usuario") from exc
    known_constraints = frozenset()
    mutation_started = False
    try:
        with operation:
            if operation.context.actor.tipo is not TipoActorBitacora.USUARIO or (
                operation.context.actor.usuario_id is None or operation.context.request_id is None
            ):
                raise AuditTransactionError()
            if delete_event is not None:
                known_constraints = get_user_referencing_constraints(db)
            mutation_started = True
            result = mutate(operation)
            prepared = _prepare_user_response(db, result) if response else result
    except IntegrityError as exc:
        operation.rollback_business()
        if delete_event is not None:
            if mutation_started and _recognized_delete_fk(exc, known_constraints):
                try:
                    operation.failure(exc, **delete_event, error_codigo="USUARIO_ELIMINACION_BLOQUEADA")
                except AuditEngineError as audit_error:
                    raise HTTPException(500, "No fue posible completar la operación de usuario") from audit_error
            raise HTTPException(
                409, "No se puede eliminar el usuario porque está ligado a registros operativos o viajes existentes",
            ) from exc
        raise HTTPException(500, "No fue posible completar la operación de usuario") from exc
    except Exception as exc:
        operation.rollback_business()
        raise HTTPException(500, "No fue posible completar la operación de usuario") from exc
    try:
        db.commit()
    except Exception as exc:
        # Closing releases local resources; NEVER assert rollback evidence or log FALLIDO
        # for an uncertain COMMIT. The dependency also closes, idempotently.
        db.close()
        raise HTTPException(500, "No fue posible confirmar la operación de usuario") from exc
    return prepared


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    audit_context: AuditContext = Depends(_get_admin_audit_context),
):
    existing_user = get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese username",
        )

    if not role_exists(db, user_in.id_rol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol especificado no existe",
        )

    return _complete_user_mutation(
        db, audit_context, lambda operation: user_audit.create_user_with_audit(db, operation, user_in), response=True,
    )


@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
def update_existing_user(
    user_id: int,
    user_in: UserAdminUpdate,
    db: Session = Depends(get_db),
    audit_context: AuditContext = Depends(_get_admin_audit_context),
):
    db_user = get_user_by_id_for_update(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user_in.username is not None:
        existing_user = get_user_by_username(db, user_in.username)
        if existing_user and existing_user.id_usuario != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro usuario con ese username",
            )

    if user_in.id_rol is not None and not role_exists(db, user_in.id_rol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol especificado no existe",
        )

    if not user_audit.has_user_changes(db_user, user_in):
        return _prepare_user_response(db, db_user)
    return _complete_user_mutation(
        db, audit_context,
        lambda operation: user_audit.update_user_with_audit(db, operation, db_user, user_in), response=True,
    )


@router.patch("/{user_id}/password", status_code=status.HTTP_200_OK)
def change_user_password(
    user_id: int,
    password_in: UserPasswordUpdate,
    db: Session = Depends(get_db),
    audit_context: AuditContext = Depends(_get_admin_audit_context),
):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    _complete_user_mutation(
        db, audit_context,
        lambda operation: user_audit.change_user_password_with_audit(db, operation, db_user, password_in),
    )
    return {"message": "Contraseña actualizada correctamente"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_user(
    user_id: int,
    db: Session = Depends(get_db),
    audit_context: AuditContext = Depends(_get_admin_audit_context),
):
    db_user = get_user_by_id_for_update(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    event_data = user_audit.user_event_data(
        "USUARIO_ELIMINADO", db_user.id_usuario, before=user_audit.snapshot_user(db_user),
    )
    _complete_user_mutation(
        db, audit_context,
        lambda operation: user_audit.delete_user_with_audit(db, operation, db_user, event_data), delete_event=event_data,
    )

    return None
