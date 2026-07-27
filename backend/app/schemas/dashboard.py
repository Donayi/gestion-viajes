from datetime import datetime, date

from pydantic import BaseModel, ConfigDict

from app.schemas.alerta import NivelAlerta
from app.schemas.kpi_operativo import KpiOperativoResumenResponse
from app.schemas.viaje_view import ViajeMapaItemResponse


class DashboardStatusCountResponse(BaseModel):
    clave: str
    nombre: str
    total: int


class DashboardViajesResumenResponse(BaseModel):
    total: int
    activos: int
    finalizados: int
    standby: int
    cancelados: int
    sin_ubicacion: int
    por_estatus: list[DashboardStatusCountResponse]


class DashboardDisponibilidadGrupoResponse(BaseModel):
    total: int
    disponibles: int
    ocupados: int
    inactivos: int


class DashboardDisponibilidadTrailersResponse(BaseModel):
    total: int
    disponibles: int
    ocupados: int
    en_mantenimiento: int
    inactivos: int


class DashboardDisponibilidadCajasResponse(BaseModel):
    total: int
    disponibles: int
    ocupadas: int
    en_mantenimiento: int
    inactivas: int


class DashboardDisponibilidadResponse(BaseModel):
    operadores: DashboardDisponibilidadGrupoResponse
    trailers: DashboardDisponibilidadTrailersResponse
    cajas: DashboardDisponibilidadCajasResponse


class DashboardAlertaItemResponse(BaseModel):
    id_alerta: int
    tipo_alerta: str
    entidad_tipo: str
    entidad_id: int
    mensaje: str
    nivel: NivelAlerta
    leida: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardAlertasResumenResponse(BaseModel):
    pendientes_total: int
    criticas_no_leidas: int
    items: list[DashboardAlertaItemResponse]


class DashboardMantenimientoEntidadResponse(BaseModel):
    id: int
    etiqueta: str
    subtitulo: str | None = None


class DashboardMantenimientoItemResponse(BaseModel):
    id_mantenimiento: int
    entidad_tipo: str
    entidad_id: int | None
    tipo_mantenimiento: str
    estatus: str
    fecha_inicio: datetime
    fecha_mantenimiento: date | None = None
    fecha_proximo_mantenimiento: date | None = None
    descripcion: str
    entidad: DashboardMantenimientoEntidadResponse


class DashboardMantenimientosResumenResponse(BaseModel):
    abiertos_total: int
    en_proceso_total: int
    proximos_total: int
    items: list[DashboardMantenimientoItemResponse]


class DashboardMapaResumenResponse(BaseModel):
    total_con_ubicacion: int
    total_sin_ubicacion: int
    items: list[ViajeMapaItemResponse]


class AdminDashboardResponse(BaseModel):
    generated_at: datetime
    viajes_resumen: DashboardViajesResumenResponse
    kpis_operativos: KpiOperativoResumenResponse
    disponibilidad: DashboardDisponibilidadResponse
    alertas: DashboardAlertasResumenResponse
    mantenimientos: DashboardMantenimientosResumenResponse
    mapa: DashboardMapaResumenResponse
