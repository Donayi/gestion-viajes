from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class OperadorBase(BaseModel):
    id_usuario: int
    alias: str
    numero_licencia: str | None = None
    licencia_vigencia: date | None = None
    sua: str | None = None
    sua_vigencia: date | None = None
    estudio_medico: date | None = None
    activo: bool = True


class OperadorCreate(OperadorBase):
    pass


class OperadorUpdate(BaseModel):
    id_usuario: int | None = None
    alias: str | None = None
    numero_licencia: str | None = None
    licencia_vigencia: date | None = None
    sua: str | None = None
    sua_vigencia: date | None = None
    estudio_medico: date | None = None
    activo: bool | None = None


class OperadorResponse(OperadorBase):
    id_operador: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)