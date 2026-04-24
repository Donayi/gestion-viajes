from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, SecretStr, field_validator


class UserBase(BaseModel):
    username: str
    nombre: str
    apellido: str
    fecha_nacimiento: date | None = None
    telefono: str | None = None
    activo: bool = True
    id_rol: int


class UserCreate(UserBase):
    password: SecretStr

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) > 72:
            raise ValueError("La password no puede exceder 72 bytes")
        return value


class UserUpdate(BaseModel):
    username: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    fecha_nacimiento: date | None = None
    telefono: str | None = None
    activo: bool | None = None
    id_rol: int | None = None
    password: SecretStr | None = None

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return value
        if len(value.get_secret_value().encode("utf-8")) > 72:
            raise ValueError("La password no puede exceder 72 bytes")
        return value


class UserResponse(BaseModel):
    id_usuario: int
    username: str
    nombre: str
    apellido: str
    fecha_nacimiento: date | None = None
    telefono: str | None = None
    activo: bool
    id_rol: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
