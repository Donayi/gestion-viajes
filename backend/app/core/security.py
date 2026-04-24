from datetime import datetime, timedelta, UTC
import hashlib

from pydantic import SecretStr
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _normalize_password(password: str | SecretStr) -> str:
    if isinstance(password, SecretStr):
        plain_password = password.get_secret_value()
    else:
        plain_password = password

    if not isinstance(plain_password, str):
        raise ValueError("La password debe ser una cadena de texto")

    if len(plain_password.encode("utf-8")) > 72:
        raise ValueError("La password no puede exceder 72 bytes")

    return plain_password


def verify_password(plain_password: str, stored_hash: str) -> bool:
    normalized_password = _normalize_password(plain_password)

    if stored_hash.startswith("$2"):
        return pwd_context.verify(normalized_password, stored_hash)

    legacy_hash = hashlib.sha256(normalized_password.encode("utf-8")).hexdigest()
    return legacy_hash == stored_hash


def get_password_hash(password: str | SecretStr) -> str:
    normalized_password = _normalize_password(password)
    return pwd_context.hash(normalized_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


__all__ = [
    "JWTError",
    "create_access_token",
    "decode_access_token",
    "get_password_hash",
    "verify_password",
]
