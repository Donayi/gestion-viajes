from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    username: str
    nombre: str
    apellido: str
    fecha_nacimiento: date | None = None
    telefono: str | None = None
    activo: bool = True
    id_rol: int


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    fecha_nacimiento: date | None = None
    telefono: str | None = None
    activo: bool | None = None
    id_rol: int | None = None
    password: str | None = None


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