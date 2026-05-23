from datetime import date, datetime, time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ViajeBase(BaseModel):
    folio_viaje_cliente: str | None = None
    id_cliente: int
    lugar_inicio: str
    lugar_destino: str
    lugar_inicio_latitud: Decimal | None = None
    lugar_inicio_longitud: Decimal | None = None
    lugar_destino_latitud: Decimal | None = None
    lugar_destino_longitud: Decimal | None = None
    tipo_carga: str | None = None
    descripcion_carga: str | None = None
    fecha_programada_salida: datetime | None = None
    fecha_carga: date | None = None
    hora_carga: time | None = None
    fecha_descarga: date | None = None
    hora_descarga: time | None = None
    hora_cita_descarga: time | None = None
    observaciones: str | None = None


class ViajeCreate(ViajeBase):
    pass


class ViajeUpdate(BaseModel):
    folio: str | None = None
    folio_viaje_cliente: str | None = None
    id_cliente: int | None = None
    lugar_inicio: str | None = None
    lugar_destino: str | None = None
    lugar_inicio_latitud: Decimal | None = None
    lugar_inicio_longitud: Decimal | None = None
    lugar_destino_latitud: Decimal | None = None
    lugar_destino_longitud: Decimal | None = None
    tipo_carga: str | None = None
    descripcion_carga: str | None = None
    fecha_programada_salida: datetime | None = None
    fecha_carga: date | None = None
    hora_carga: time | None = None
    fecha_descarga: date | None = None
    hora_descarga: time | None = None
    fecha_inicio: datetime | None = None
    fecha_llegada: datetime | None = None
    fecha_entrega: date | None = None
    hora_entrega: time | None = None
    hora_cita_descarga: time | None = None
    observaciones: str | None = None
    id_operador_actual: int | None = None
    id_trailer_actual: int | None = None
    id_caja_actual: int | None = None
    id_estatus_actual: int | None = None
    updated_by: int | None = None


class ViajeResponse(BaseModel):
    id_viaje: int
    folio: str
    folio_viaje_cliente: str | None = None
    id_cliente: int
    lugar_inicio: str
    lugar_destino: str
    lugar_inicio_latitud: Decimal | None = None
    lugar_inicio_longitud: Decimal | None = None
    lugar_destino_latitud: Decimal | None = None
    lugar_destino_longitud: Decimal | None = None
    tipo_carga: str | None = None
    descripcion_carga: str | None = None
    id_estatus_actual: int
    id_operador_actual: int | None = None
    id_trailer_actual: int | None = None
    id_caja_actual: int | None = None
    fecha_programada_salida: datetime | None = None
    fecha_carga: date | None = None
    hora_carga: time | None = None
    fecha_descarga: date | None = None
    hora_descarga: time | None = None
    fecha_inicio: datetime | None = None
    fecha_llegada: datetime | None = None
    fecha_entrega: date | None = None
    hora_entrega: time | None = None
    hora_cita_descarga: time | None = None
    observaciones: str | None = None
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ViajeAsignacionCreate(BaseModel):
    id_operador: int
    id_trailer: int
    id_caja: int | None = None
    created_by: int | None = None
    motivo: str | None = None
    comentario: str | None = None


class ViajeAsignacionResponse(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class ViajeCambioEstatus(BaseModel):
    id_estatus_destino: int
    changed_by: int | None = None
    comentario: str | None = None


class HistorialEstatusViajeResponse(BaseModel):
    id_historial: int
    id_viaje: int
    id_estatus: int
    comentario: str | None = None
    changed_by: int | None = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecursoDisponibleResponse(BaseModel):
    id: int
    descripcion: str

class CambioEstatusResponse(BaseModel):
    id_viaje: int
    id_estatus_actual: int
    mensaje: str

    model_config = ConfigDict(from_attributes=True)


class OperadorDisponibleResponse(BaseModel):
    id_operador: int
    alias: str


class TrailerDisponibleResponse(BaseModel):
    id_trailer: int
    numero_economico: str
    placas: str


class CajaDisponibleResponse(BaseModel):
    id_caja: int
    numero_economico: str | None = None
    placas: str


class DisponibilidadViajeActualResumen(BaseModel):
    id_viaje: int
    folio: str
    estatus_clave: str | None = None


class OperadorDisponibilidadResumen(BaseModel):
    id_operador: int
    alias: str
    username: str | None = None
    nombre_completo: str | None = None
    numero_licencia: str | None = None
    activo: bool
    disponible: bool
    viaje_actual: DisponibilidadViajeActualResumen | None = None
    motivo_no_disponible: str | None = None


class TrailerDisponibilidadResumen(BaseModel):
    id_trailer: int
    numero_economico: str
    placas: str
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    activo: bool
    disponible: bool
    viaje_actual: DisponibilidadViajeActualResumen | None = None
    motivo_no_disponible: str | None = None


class CajaDisponibilidadResumen(BaseModel):
    id_caja: int
    numero_economico: str | None = None
    placas: str
    tipo_caja: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    activo: bool
    disponible: bool
    viaje_actual: DisponibilidadViajeActualResumen | None = None
    motivo_no_disponible: str | None = None


class DisponibilidadResumenResponse(BaseModel):
    operadores: list[OperadorDisponibilidadResumen]
    trailers: list[TrailerDisponibilidadResumen]
    cajas: list[CajaDisponibilidadResumen]

class ViajeComentarioAccion(BaseModel):
    changed_by: int | None = None
    comentario: str | None = None


class ViajeReasignacionCreate(BaseModel):
    id_operador: int
    id_trailer: int
    id_caja: int | None = None
    created_by: int | None = None
    motivo: str | None = None
    comentario: str | None = None


class TransicionDisponibleResponse(BaseModel):
    id_estatus_destino: int
    clave: str
    nombre: str
    requiere_comentario: bool
    requiere_evidencia: bool
