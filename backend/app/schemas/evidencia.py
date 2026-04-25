from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ViajeEvidenciaBase(BaseModel):
    id_tipo_evidencia: int
    id_archivo: int
    id_operador: int | None = None
    comentario: str | None = None
    fecha_captura: datetime | None = None
    latitud: float | None = None
    longitud: float | None = None


class ViajeEvidenciaCreate(ViajeEvidenciaBase):
    pass


class ViajeEvidenciaUpdate(BaseModel):
    id_tipo_evidencia: int | None = None
    id_archivo: int | None = None
    id_operador: int | None = None
    comentario: str | None = None
    fecha_captura: datetime | None = None
    latitud: float | None = None
    longitud: float | None = None


class ViajeEvidenciaResponse(BaseModel):
    id_evidencia: int
    id_viaje: int
    id_tipo_evidencia: int
    id_operador: int | None = None
    id_archivo: int
    comentario: str | None = None
    fecha_captura: datetime
    latitud: float | None = None
    longitud: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TipoEvidenciaResponse(BaseModel):
    id_tipo_evidencia: int
    nombre: str
    descripcion: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ArchivoStoragePruebaResponse(BaseModel):
    id_archivo: int
    proveedor: str
    bucket: str
    file_key: str
    nombre_original: str | None = None
    nombre_guardado: str | None = None
    extension: str | None = None
    content_type: str | None = None
    url_publica: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PresignUploadRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int | None = None


class PresignUploadResponse(BaseModel):
    upload_url: str
    file_key: str
    id_archivo: int
