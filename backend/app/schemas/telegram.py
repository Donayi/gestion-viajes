from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelegramDestinatarioBase(BaseModel):
    nombre: str
    chat_id: str
    activo: bool = True
    recibe_documentos: bool = True
    recibe_mantenimiento: bool = True
    recibe_viajes: bool = True


class TelegramDestinatarioCreate(TelegramDestinatarioBase):
    pass


class TelegramDestinatarioUpdate(BaseModel):
    nombre: str | None = None
    chat_id: str | None = None
    activo: bool | None = None
    recibe_documentos: bool | None = None
    recibe_mantenimiento: bool | None = None
    recibe_viajes: bool | None = None


class TelegramDestinatarioResponse(TelegramDestinatarioBase):
    id_destinatario: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TelegramTestResponse(BaseModel):
    enviado: bool
    mensaje: str
    destinatario: TelegramDestinatarioResponse


class ProcesarNotificacionesResponse(BaseModel):
    alertas_evaluadas: int
    alertas_enviadas: int
    alertas_sin_destinatario: int
    alertas_omitidas: int
    alertas_fallidas: int
