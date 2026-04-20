from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ClienteBase(BaseModel):
    nombre_razon_social: str
    rfc: str | None = None
    direccion: str | None = None
    cp: str | None = None
    regimen_fiscal: str | None = None
    tiempo_credito: int | None = None
    contacto_nombre: str | None = None
    contacto_telefono: str | None = None
    contacto_email: str | None = None
    activo: bool = True


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre_razon_social: str | None = None
    rfc: str | None = None
    direccion: str | None = None
    cp: str | None = None
    regimen_fiscal: str | None = None
    tiempo_credito: int | None = None
    contacto_nombre: str | None = None
    contacto_telefono: str | None = None
    contacto_email: str | None = None
    activo: bool | None = None


class ClienteResponse(ClienteBase):
    id_cliente: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)