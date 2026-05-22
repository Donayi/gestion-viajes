from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.db.deps import get_db
from app.crud.crud_usuarios import (
    create_user,
    delete_user,
    get_user_by_id,
    get_user_by_username,
    get_users,
    role_exists,
    update_user_admin,
    update_user_password,
)
from app.schemas.user import UserAdminUpdate, UserCreate, UserPasswordUpdate, UserResponse

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
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

    return create_user(db, user_in)


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
    _=Depends(require_admin),
):
    db_user = get_user_by_id(db, user_id)
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

    return update_user_admin(db, db_user, user_in)


@router.patch("/{user_id}/password", status_code=status.HTTP_200_OK)
def change_user_password(
    user_id: int,
    password_in: UserPasswordUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    update_user_password(db, db_user, password_in)
    return {"message": "Contraseña actualizada correctamente"}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_user(
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

    try:
        delete_user(db, db_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el usuario porque está ligado a registros operativos o viajes existentes",
        ) from exc

    return None
