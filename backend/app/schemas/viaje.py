from datetime import date, datetime, time
from pydantic import BaseModel, ConfigDict


class ViajeBase(BaseModel):
    folio: str
    id_cliente: int
    lugar_inicio: str
    lugar_destino: str
    tipo_carga: str | None = None
    descripcion_carga: str | None = None
    fecha_programada_salida: datetime | None = None
    observaciones: str | None = None


class ViajeCreate(ViajeBase):
    pass


class ViajeUpdate(BaseModel):
    folio: str | None = None
    id_cliente: int | None = None
    lugar_inicio: str | None = None
    lugar_destino: str | None = None
    tipo_carga: str | None = None
    descripcion_carga: str | None = None
    fecha_programada_salida: datetime | None = None
    fecha_inicio: datetime | None = None
    fecha_llegada: datetime | None = None
    fecha_entrega: date | None = None
    hora_entrega: time | None = None
    observaciones: str | None = None
    id_operador_actual: int | None = None
    id_trailer_actual: int | None = None
    id_caja_actual: int | None = None
    id_estatus_actual: int | None = None
    updated_by: int | None = None


class ViajeResponse(BaseModel):
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