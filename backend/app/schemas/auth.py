from datetime import date

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BootstrapAdminCreate(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1)
    nombre: str = Field(min_length=1, max_length=150)
    apellido: str = Field(min_length=1, max_length=150)
    telefono: str | None = Field(default=None, max_length=50)
    fecha_nacimiento: date | None = None


class BootstrapAdminResponse(BaseModel):
    id_usuario: int
    username: str
    nombre: str
    apellido: str
    rol: str


class CurrentUserResponse(BaseModel):
    id_usuario: int
    username: str
    nombre: str
    apellido: str
    rol: str
    id_operador: int | None = None
