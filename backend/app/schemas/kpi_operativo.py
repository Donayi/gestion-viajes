from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class KpiOperativoResumenResponse(BaseModel):
    total_viajes_con_eventos: int
    km_total_recorridos: float
    km_promedio_por_viaje: float
    diesel_total_consumido_estimado: float
    diesel_promedio_consumido: float
    numero_total_standbys: int
    viajes_finalizados_con_kpi: int


class KpiOperativoViajeRowResponse(BaseModel):
    id_viaje: int
    folio: str
    cliente: str
    operador: str | None = None
    km_inicio: float | None = None
    km_final: float | None = None
    km_recorridos: float | None = None
    diesel_inicio: float | None = None
    diesel_final: float | None = None
    diesel_consumido: float | None = None
    numero_standbys: int
    ubicacion_inicio: str | None = None
    ubicacion_final: str | None = None
    fecha_inicio: datetime | None = None
    fecha_finalizacion: datetime | None = None
    kpi_completo: bool
    kpi_valido: bool
    anomalia: str | None = None


class KpiOperativoDashboardResponse(BaseModel):
    resumen: KpiOperativoResumenResponse
    viajes: list[KpiOperativoViajeRowResponse]


class KpiOperativoFilterParams(BaseModel):
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    id_operador: int | None = None
    id_cliente: int | None = None
    id_estatus: int | None = None
    solo_completos: bool = False

    model_config = ConfigDict(from_attributes=True)
