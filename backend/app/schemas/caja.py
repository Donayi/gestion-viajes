from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class CajaBase(BaseModel):
    numero_economico: str | None = None
    placas: str
    tipo_caja: str | None = None
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


class CajaCreate(CajaBase):
    pass


class CajaUpdate(BaseModel):
    numero_economico: str | None = None
    placas: str | None = None
    tipo_caja: str | None = None
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


class CajaResponse(CajaBase):
    id_caja: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)