from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


NivelAlerta = Literal["INFO", "WARNING", "CRITICAL"]


class AlertaResponse(BaseModel):
    id_alerta: int
    tipo_alerta: str
    entidad_tipo: str
    entidad_id: int
    mensaje: str
    nivel: NivelAlerta
    leida: bool
    requiere_notificacion: bool
    notificada: bool
    canal_notificacion: str | None = None
    fecha_notificacion: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerarAlertasResponse(BaseModel):
    nuevas_alertas_creadas: int
    omitidas_por_duplicadas: int
    alertas_creadas: list[AlertaResponse] = []
