from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class TrailerBase(BaseModel):
    numero_economico: str
    placas: str
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    poliza_seguro: str | None = None
    seguro_vigencia: date | None = None
    tarjeta_circulacion: str | None = None
    tarjeta_vigencia: date | None = None
    verificacion: str | None = None
    verificacion_vigencia: date | None = None
    activo: bool = True


class TrailerCreate(TrailerBase):
    pass


class TrailerUpdate(BaseModel):
    numero_economico: str | None = None
    placas: str | None = None
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    poliza_seguro: str | None = None
    seguro_vigencia: date | None = None
    tarjeta_circulacion: str | None = None
    tarjeta_vigencia: date | None = None
    verificacion: str | None = None
    verificacion_vigencia: date | None = None
    activo: bool | None = None


class TrailerResponse(TrailerBase):
    id_trailer: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)