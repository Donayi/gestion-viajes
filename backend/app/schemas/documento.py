from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DocumentoCreate(BaseModel):
    id_tipo_documento: int
    id_archivo: int
    fecha_emision: date | None = None
    fecha_expiracion: date | None = None
    estatus: str = "VIGENTE"
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
    estatus: str
    subido_por: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TipoDocumentoResponse(BaseModel):
    id_tipo_documento: int
    nombre: str
    descripcion: str | None = None
    aplica_a: str
    requiere_vigencia: bool

    model_config = ConfigDict(from_attributes=True)
