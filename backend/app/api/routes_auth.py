from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps_auth import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.crud_usuarios import admin_exists, authenticate_user, create_bootstrap_admin
from app.db.deps import get_db
from app.models.models import Usuario
from app.schemas.auth import (
    BootstrapAdminCreate,
    BootstrapAdminResponse,
    CurrentUserResponse,
    TokenResponse,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/bootstrap-admin",
    response_model=BootstrapAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_admin(
    bootstrap_in: BootstrapAdminCreate,
    db: Session = Depends(get_db),
):
    if admin_exists(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario administrador. El bootstrap inicial ya no esta disponible",
        )

    try:
        user = create_bootstrap_admin(db, bootstrap_in)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_409_CONFLICT if "bootstrap inicial" in detail else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from exc

    return BootstrapAdminResponse(
        id_usuario=user.id_usuario,
        username=user.username,
        nombre=user.nombre,
        apellido=user.apellido,
        rol="ADMIN",
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: Usuario = Depends(get_current_user),
):
    return CurrentUserResponse(
        id_usuario=current_user.id_usuario,
        username=current_user.username,
        nombre=current_user.nombre,
        apellido=current_user.apellido,
        rol=current_user.rol.nombre.upper(),
        id_operador=current_user.operador.id_operador if current_user.operador else None,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username o password incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id_usuario),
            "username": user.username,
            "role": user.rol.nombre.upper(),
            "operator_id": user.operador.id_operador if user.operador else None,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return TokenResponse(access_token=access_token)
