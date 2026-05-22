from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from app.schemas.evidencia import ArchivoStorageResumenResponse


class DocumentoCreate(BaseModel):
    id_tipo_documento: int
    id_archivo: int
    fecha_emision: date | None = None
    fecha_expiracion: date | None = None
    estatus: str = "VIGENTE"
    comentario: str | None = None
    activo: bool = True
    subido_por: int | None = None


class DocumentoResponse(BaseModel):
    id_documento: int
    id_tipo_documento: int
    id_operador: int | None = None
    id_trailer: int | None = None
    id_caja: int | None = None
    id_viaje: int | None = None
    id_archivo: int
    fecha_emision: date | None = None
    fecha_expiracion: date | None = None
    comentario: str | None = None
    estatus: str
    activo: bool
    subido_por: int | None = None
    created_at: datetime
    updated_at: datetime
    tipo_documento: "TipoDocumentoResponse | None" = None
    archivo: ArchivoStorageResumenResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class TipoDocumentoResponse(BaseModel):
    id_tipo_documento: int
    nombre: str
    descripcion: str | None = None
    aplica_a: str
    requiere_vigencia: bool

    model_config = ConfigDict(from_attributes=True)


EntidadDocumentoTipo = Literal["OPERADOR", "TRAILER", "CAJA"]


class DocumentoAdminCreate(BaseModel):
    entidad_tipo: EntidadDocumentoTipo
    entidad_id: int
    id_tipo_documento: int
    id_archivo: int
    comentario: str | None = None
    fecha_vencimiento: date | None = None
    activo: bool = True


class DocumentoAdminUpdate(BaseModel):
    id_tipo_documento: int | None = None
    id_archivo: int | None = None
    comentario: str | None = None
    fecha_vencimiento: date | None = None
    activo: bool | None = None


class DocumentoAdminResponse(BaseModel):
    id_documento: int
    entidad_tipo: EntidadDocumentoTipo
    entidad_id: int
    id_tipo_documento: int
    id_archivo: int
    comentario: str | None = None
    fecha_vencimiento: date | None = None
    estatus: str
    activo: bool
    subido_por: int | None = None
    created_at: datetime
    updated_at: datetime
    tipo_documento: TipoDocumentoResponse | None = None
    archivo: ArchivoStorageResumenResponse | None = None

    model_config = ConfigDict(from_attributes=True)
