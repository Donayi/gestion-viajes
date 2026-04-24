from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.crud.crud_usuarios import get_user_with_role_and_operador
from app.db.deps import get_db
from app.models.models import Operador, Usuario
from app.core.security import JWTError, decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No fue posible validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = int(subject)
    except (JWTError, ValueError):
        raise credentials_exception

    user = get_user_with_role_and_operador(db, user_id)
    if not user:
        raise credentials_exception

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario está inactivo",
        )

    return user


def require_roles(*roles: str) -> Callable[..., Usuario]:
    allowed_roles = {role.upper() for role in roles}

    def dependency(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        current_role = current_user.rol.nombre.upper()
        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a este recurso",
            )
        return current_user

    return dependency


require_admin = require_roles("ADMIN")
require_admin_or_operador = require_roles("ADMIN", "OPERADOR")


def get_current_operador_or_403(
    current_user: Usuario = Depends(get_current_user),
) -> Operador:
    if current_user.rol.nombre.upper() != "OPERADOR" or current_user.operador is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario actual no tiene perfil de operador",
        )
    return current_user.operador
