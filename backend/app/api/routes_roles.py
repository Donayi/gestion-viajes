from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.db.deps import get_db
from app.crud.crud_roles import (
    create_role,
    delete_role,
    get_role_by_id,
    get_role_by_name,
    get_roles,
    update_role,
)
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/roles", tags=["Roles"])


PROTECTED_ROLE_NAMES = {"ADMIN", "OPERADOR", "MANTENIMIENTO"}


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_new_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    existing_role = get_role_by_name(db, role_in.nombre)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con ese nombre",
        )

    return create_role(db, role_in)


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
    _=Depends(require_admin),
):
    db_role = get_role_by_id(db, role_id)
    if not db_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    current_role_name = (db_role.nombre or "").strip().upper()
    if current_role_name in PROTECTED_ROLE_NAMES and role_in.nombre is not None:
        new_role_name = role_in.nombre.strip().upper()
        if new_role_name != current_role_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede renombrar el rol base {current_role_name}",
            )

    if role_in.nombre is not None:
        existing_role = get_role_by_name(db, role_in.nombre)
        if existing_role and existing_role.id_rol != role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro rol con ese nombre",
            )

    return update_role(db, db_role, role_in)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_role(
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

    current_role_name = (db_role.nombre or "").strip().upper()
    if current_role_name in PROTECTED_ROLE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el rol base {current_role_name}",
        )

    try:
        delete_role(db, db_role)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el rol porque tiene usuarios ligados",
        ) from exc

    return None
