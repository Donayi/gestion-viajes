from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from app.schemas.evidencia import ArchivoStorageResumenResponse


EntidadMantenimientoTipo = Literal["TRAILER", "CAJA"]
TipoMantenimiento = Literal["PREVENTIVO", "CORRECTIVO", "REPARACION"]
EstatusMantenimiento = Literal["ABIERTO", "EN_PROCESO", "CERRADO", "CANCELADO"]
TipoArchivoMantenimiento = Literal["FOTO_ANTES", "FOTO_DESPUES", "FACTURA", "DIAGNOSTICO", "OTRO"]


class MantenimientoChecklistItemBase(BaseModel):
    nombre: str
    descripcion: str | None = None
    completado: bool = False
    observaciones: str | None = None


class MantenimientoChecklistEvidenciaCreate(BaseModel):
    id_archivo: int
    comentario: str | None = None


class MantenimientoChecklistEvidenciaUpdate(BaseModel):
    comentario: str | None = None
    activo: bool | None = None


class MantenimientoChecklistEvidenciaResponse(BaseModel):
    id_checklist_evidencia: int
    id_item: int
    id_archivo: int
    comentario: str | None = None
    activo: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
    archivo: ArchivoStorageResumenResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class MantenimientoChecklistItemUpdate(BaseModel):
    completado: bool | None = None
    observaciones: str | None = None


class MantenimientoChecklistItemResponse(MantenimientoChecklistItemBase):
    id_item: int
    id_mantenimiento: int
    created_at: datetime
    updated_at: datetime
    evidencias: list[MantenimientoChecklistEvidenciaResponse] = []

    model_config = ConfigDict(from_attributes=True)


class MantenimientoArchivoCreate(BaseModel):
    id_archivo: int
    tipo_archivo: TipoArchivoMantenimiento
    comentario: str | None = None


class MantenimientoArchivoUpdate(BaseModel):
    tipo_archivo: TipoArchivoMantenimiento | None = None
    comentario: str | None = None
    activo: bool | None = None


class MantenimientoArchivoResponse(BaseModel):
    id_mantenimiento_archivo: int
    id_mantenimiento: int
    id_archivo: int
    tipo_archivo: TipoArchivoMantenimiento
    comentario: str | None = None
    activo: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
    archivo: ArchivoStorageResumenResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class MantenimientoCreate(BaseModel):
    entidad_tipo: EntidadMantenimientoTipo
    entidad_id: int
    tipo_mantenimiento: TipoMantenimiento
    fecha_mantenimiento: date | None = None
    fecha_proximo_mantenimiento: date | None = None
    kilometraje: float | None = None
    descripcion: str
    observaciones: str | None = None


class MantenimientoUpdate(BaseModel):
    tipo_mantenimiento: TipoMantenimiento | None = None
    estatus: EstatusMantenimiento | None = None
    fecha_mantenimiento: date | None = None
    fecha_proximo_mantenimiento: date | None = None
    kilometraje: float | None = None
    descripcion: str | None = None
    observaciones: str | None = None


class MantenimientoCambioEstado(BaseModel):
    observaciones: str | None = None


class MantenimientoResumenEntidad(BaseModel):
    id: int
    etiqueta: str
    subtitulo: str | None = None


class MantenimientoTrailerDisponibleResponse(BaseModel):
    id_trailer: int
    numero_economico: str
    placas: str

    model_config = ConfigDict(from_attributes=True)


class MantenimientoCajaDisponibleResponse(BaseModel):
    id_caja: int
    numero_economico: str | None = None
    placas: str

    model_config = ConfigDict(from_attributes=True)


class MantenimientoRecursosDisponiblesResponse(BaseModel):
    trailers: list[MantenimientoTrailerDisponibleResponse]
    cajas: list[MantenimientoCajaDisponibleResponse]


class MantenimientoResponse(BaseModel):
    id_mantenimiento: int
    entidad_tipo: EntidadMantenimientoTipo
    entidad_id: int
    id_trailer: int | None = None
    id_caja: int | None = None
    tipo_mantenimiento: TipoMantenimiento
    estatus: EstatusMantenimiento
    fecha_inicio: datetime
    fecha_mantenimiento: date | None = None
    fecha_proximo_mantenimiento: date | None = None
    fecha_fin: datetime | None = None
    kilometraje: float | None = None
    descripcion: str
    observaciones: str | None = None
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime
    entidad: MantenimientoResumenEntidad
    checklist_items: list[MantenimientoChecklistItemResponse] = []
    archivos: list[MantenimientoArchivoResponse] = []

    model_config = ConfigDict(from_attributes=True)
