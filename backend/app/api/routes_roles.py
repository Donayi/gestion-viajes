from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.db.deps import get_db
from app.crud.crud_roles import (
    create_role,
    get_role_by_id,
    get_role_by_name,
    get_roles,
)
from app.schemas.role import RoleCreate, RoleResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


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
