from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from app.schemas.evento_operativo import EventoOperativoViajeResponse


class ClienteResumenResponse(BaseModel):
    id_cliente: int
    nombre_razon_social: str
    rfc: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EstatusViajeResumenResponse(BaseModel):
    id_estatus: int
    clave: str
    nombre: str
    es_terminal: bool
    requiere_evidencia: bool

    model_config = ConfigDict(from_attributes=True)


class OperadorResumenResponse(BaseModel):
    id_operador: int
    alias: str

    model_config = ConfigDict(from_attributes=True)


class TrailerResumenResponse(BaseModel):
    id_trailer: int
    numero_economico: str
    placas: str

    model_config = ConfigDict(from_attributes=True)


class CajaResumenResponse(BaseModel):
    id_caja: int
    numero_economico: str | None = None
    placas: str

    model_config = ConfigDict(from_attributes=True)


class UsuarioResumenResponse(BaseModel):
    id_usuario: int
    username: str
    nombre: str
    apellido: str

    model_config = ConfigDict(from_attributes=True)


class ViajeListItemResponse(BaseModel):
    id_viaje: int
    folio: str
    id_cliente: int
    lugar_inicio: str
    lugar_destino: str
    tipo_carga: str | None = None
    descripcion_carga: str | None = None
    id_estatus_actual: int
    id_operador_actual: int | None = None
    id_trailer_actual: int | None = None
    id_caja_actual: int | None = None
    fecha_programada_salida: datetime | None = None
    fecha_inicio: datetime | None = None
    fecha_llegada: datetime | None = None
    fecha_entrega: date | None = None
    hora_entrega: time | None = None
    observaciones: str | None = None
    created_at: datetime
    updated_at: datetime
    cliente: ClienteResumenResponse
    estatus_actual: EstatusViajeResumenResponse
    operador_actual: OperadorResumenResponse | None = None
    trailer_actual: TrailerResumenResponse | None = None
    caja_actual: CajaResumenResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ViajeDetailResponse(BaseModel):
    id_viaje: int
    folio: str
    id_cliente: int
    lugar_inicio: str
    lugar_destino: str
    tipo_carga: str | None = None
    descripcion_carga: str | None = None
    id_estatus_actual: int
    id_operador_actual: int | None = None
    id_trailer_actual: int | None = None
    id_caja_actual: int | None = None
    fecha_programada_salida: datetime | None = None
    fecha_inicio: datetime | None = None
    fecha_llegada: datetime | None = None
    fecha_entrega: date | None = None
    hora_entrega: time | None = None
    observaciones: str | None = None
    created_at: datetime
    updated_at: datetime
    cliente: ClienteResumenResponse
    estatus_actual: EstatusViajeResumenResponse
    operador_actual: OperadorResumenResponse | None = None
    trailer_actual: TrailerResumenResponse | None = None
    caja_actual: CajaResumenResponse | None = None
    usuario_creador: UsuarioResumenResponse | None = None
    usuario_actualizador: UsuarioResumenResponse | None = None
    eventos_operativos: list[EventoOperativoViajeResponse] = []

    model_config = ConfigDict(from_attributes=True)


class HistorialEstatusViajeEnrichedResponse(BaseModel):
    id_historial: int
    id_viaje: int
    id_estatus: int
    comentario: str | None = None
    changed_by: int | None = None
    changed_at: datetime
    estatus: EstatusViajeResumenResponse
    usuario_cambio: UsuarioResumenResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ViajeAsignacionEnrichedResponse(BaseModel):
    id_asignacion: int
    id_viaje: int
    id_operador: int | None = None
    id_trailer: int | None = None
    id_caja: int | None = None
    activo: bool
    fecha_asignacion: datetime
    fecha_inicio_operacion: datetime | None = None
    fecha_fin_asignacion: datetime | None = None
    motivo: str | None = None
    comentario: str | None = None
    created_by: int | None = None
    created_at: datetime
    operador: OperadorResumenResponse | None = None
    trailer: TrailerResumenResponse | None = None
    caja: CajaResumenResponse | None = None
    usuario_creador: UsuarioResumenResponse | None = None

    model_config = ConfigDict(from_attributes=True)
