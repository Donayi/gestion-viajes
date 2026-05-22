from datetime import date

from pydantic import BaseModel


class KpiPeriodoResponse(BaseModel):
    fecha_desde: date | None = None
    fecha_hasta: date | None = None


class KpiSerieItemResponse(BaseModel):
    etiqueta: str
    valor: float


class KpiOperadorItemResponse(BaseModel):
    id_operador: int
    nombre: str
    nombre_operador: str
    nombre_completo: str | None = None
    viajes_semana: int
    viajes_mes: int
    km_recorridos: float


class KpiOperadoresResponse(BaseModel):
    periodo: KpiPeriodoResponse
    total_viajes_semana: int
    total_viajes_mes: int
    total_km_recorridos: float
    series_semanales: list[KpiSerieItemResponse]
    series_mensuales: list[KpiSerieItemResponse]
    operadores: list[KpiOperadorItemResponse]


class KpiTrailerViajeDetalleResponse(BaseModel):
    id_viaje: int
    folio: str
    id_trailer: int
    numero_economico: str
    km_recorridos: float | None = None
    diesel_consumido_pct: float | None = None
    rendimiento_km_por_pct_diesel: float | None = None
    consumo_valido: bool


class KpiTrailerItemResponse(BaseModel):
    id_trailer: int
    numero_economico: str
    placas: str | None = None
    km_recorridos: float
    diesel_consumido_pct: float
    rendimiento_km_por_pct_diesel: float | None = None
    viajes: list[KpiTrailerViajeDetalleResponse]


class KpiTrailersResponse(BaseModel):
    periodo: KpiPeriodoResponse
    total_km_recorridos: float
    total_diesel_consumido_pct: float
    rendimiento_promedio_km_por_pct_diesel: float | None = None
    trailers: list[KpiTrailerItemResponse]


class KpiClienteItemResponse(BaseModel):
    id_cliente: int
    nombre: str
    nombre_razon_social: str
    viajes_terminados_semana: int
    viajes_terminados_mes: int
    viajes_en_espera: int


class KpiClientesResponse(BaseModel):
    periodo: KpiPeriodoResponse
    total_viajes_terminados_semana: int
    total_viajes_terminados_mes: int
    total_viajes_en_espera: int
    series_semanales: list[KpiSerieItemResponse]
    series_mensuales: list[KpiSerieItemResponse]
    clientes: list[KpiClienteItemResponse]
