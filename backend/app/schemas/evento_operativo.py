from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


TipoEventoOperativo = Literal["INICIO_VIAJE", "STANDBY", "FINALIZACION_VIAJE"]


class EventoOperativoViajePayload(BaseModel):
    kilometraje: Decimal = Field(ge=0)
    nivel_diesel: Decimal = Field(ge=0, le=100)
    ubicacion: str
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    comentario: str | None = None

    @model_validator(mode="after")
    def validar_coordenadas_y_ubicacion(self) -> "EventoOperativoViajePayload":
        if not self.ubicacion or not self.ubicacion.strip():
            raise ValueError("La ubicacion es obligatoria para esta accion")

        if (self.latitud is None) != (self.longitud is None):
            raise ValueError("Latitud y longitud deben enviarse juntas si se captura geolocalizacion")

        self.ubicacion = self.ubicacion.strip()
        if self.comentario is not None:
            self.comentario = self.comentario.strip() or None
        return self


class EventoOperativoViajeResponse(BaseModel):
    id_evento: int
    id_viaje: int
    id_operador: int | None = None
    id_trailer: int | None = None
    id_caja: int | None = None
    tipo_evento: TipoEventoOperativo
    kilometraje: Decimal
    nivel_diesel: Decimal
    ubicacion: str
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    comentario: str | None = None
    created_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
