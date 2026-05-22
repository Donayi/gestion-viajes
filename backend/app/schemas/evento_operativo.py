from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.evidencia import EvidenciaOperativaInput, ViajeEvidenciaResponse


TipoEventoOperativo = Literal[
    "INICIO_CARGA",
    "INICIO_VIAJE",
    "REINICIO_VIAJE",
    "RETRASO",
    "STANDBY_SOLICITADO",
    "STANDBY",
    "FINALIZACION_VIAJE",
]


class EventoOperativoBasePayload(BaseModel):
    ubicacion: str
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    comentario: str | None = None
    evidencias: list[EvidenciaOperativaInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_coordenadas_y_ubicacion(self) -> "EventoOperativoBasePayload":
        if not self.ubicacion or not self.ubicacion.strip():
            raise ValueError("La ubicacion es obligatoria para esta accion")

        if (self.latitud is None) != (self.longitud is None):
            raise ValueError("Latitud y longitud deben enviarse juntas si se captura geolocalizacion")

        self.ubicacion = self.ubicacion.strip()
        if self.comentario is not None:
            self.comentario = self.comentario.strip() or None
        return self


class EventoOperativoCargaPayload(EventoOperativoBasePayload):
    pass


class EventoOperativoRetrasoPayload(EventoOperativoBasePayload):
    comentario: str

    @model_validator(mode="after")
    def validar_comentario(self) -> "EventoOperativoRetrasoPayload":
        if not self.comentario or not self.comentario.strip():
            raise ValueError("El comentario es obligatorio para marcar retraso")
        self.comentario = self.comentario.strip()
        return self


class EventoOperativoViajePayload(EventoOperativoBasePayload):
    kilometraje: Decimal = Field(ge=0)
    nivel_diesel: Decimal = Field(ge=0, le=100)


class EventoOperativoViajeUpdatePayload(BaseModel):
    kilometraje: Decimal | None = Field(default=None, ge=0)
    nivel_diesel: Decimal | None = Field(default=None, ge=0, le=100)
    ubicacion: str | None = None
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    comentario: str | None = None

    @model_validator(mode="after")
    def validar_payload_actualizacion(self) -> "EventoOperativoViajeUpdatePayload":
        if self.ubicacion is not None:
            self.ubicacion = self.ubicacion.strip()
            if not self.ubicacion:
                raise ValueError("La ubicacion no puede ser vacia")

        if (self.latitud is None) != (self.longitud is None):
            raise ValueError("Latitud y longitud deben enviarse juntas si se captura geolocalizacion")

        if self.comentario is not None:
            self.comentario = self.comentario.strip() or None

        return self


class EventoOperativoOperadorResumenResponse(BaseModel):
    id_operador: int
    alias: str

    model_config = ConfigDict(from_attributes=True)


class EventoOperativoTrailerResumenResponse(BaseModel):
    id_trailer: int
    numero_economico: str
    placas: str

    model_config = ConfigDict(from_attributes=True)


class EventoOperativoCajaResumenResponse(BaseModel):
    id_caja: int
    numero_economico: str | None = None
    placas: str

    model_config = ConfigDict(from_attributes=True)


class EventoOperativoViajeResponse(BaseModel):
    id_evento: int
    id_viaje: int
    id_operador: int | None = None
    id_trailer: int | None = None
    id_caja: int | None = None
    tipo_evento: TipoEventoOperativo
    kilometraje: Decimal | None = None
    nivel_diesel: Decimal | None = None
    ubicacion: str
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    comentario: str | None = None
    created_by: int | None = None
    created_at: datetime
    operador: EventoOperativoOperadorResumenResponse | None = None
    trailer: EventoOperativoTrailerResumenResponse | None = None
    caja: EventoOperativoCajaResumenResponse | None = None
    evidencias: list[ViajeEvidenciaResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
