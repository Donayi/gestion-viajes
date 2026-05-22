export type KpiOperativoResumen = {
  total_viajes_con_eventos: number;
  km_total_recorridos: number;
  km_promedio_por_viaje: number;
  diesel_total_consumido_estimado: number;
  diesel_promedio_consumido: number;
  numero_total_standbys: number;
  viajes_finalizados_con_kpi: number;
};

export type KpiOperativoViajeRow = {
  id_viaje: number;
  folio: string;
  cliente: string;
  operador: string | null;
  km_inicio: number | null;
  km_final: number | null;
  km_recorridos: number | null;
  diesel_inicio: number | null;
  diesel_final: number | null;
  diesel_consumido: number | null;
  numero_standbys: number;
  ubicacion_inicio: string | null;
  ubicacion_final: string | null;
  fecha_inicio: string | null;
  fecha_finalizacion: string | null;
  kpi_completo: boolean;
  kpi_valido: boolean;
  anomalia: string | null;
};

export type KpiOperativoDashboard = {
  resumen: KpiOperativoResumen;
  viajes: KpiOperativoViajeRow[];
};

export type KpiOperativoFilters = {
  fecha_desde?: string;
  fecha_hasta?: string;
  id_operador?: number;
  id_cliente?: number;
  id_estatus?: number;
  solo_completos?: boolean;
};

export type KpiSerieItem = {
  etiqueta: string;
  valor: number;
};

export type KpiOperadorItem = {
  id_operador: number;
  nombre: string;
  nombre_operador: string;
  nombre_completo: string | null;
  viajes_semana: number;
  viajes_mes: number;
  km_recorridos: number;
};

export type KpiOperadoresResponse = {
  periodo: { fecha_desde: string | null; fecha_hasta: string | null };
  total_viajes_semana: number;
  total_viajes_mes: number;
  total_km_recorridos: number;
  series_semanales: KpiSerieItem[];
  series_mensuales: KpiSerieItem[];
  operadores: KpiOperadorItem[];
};

export type KpiTrailerViajeDetalle = {
  id_viaje: number;
  folio: string;
  id_trailer: number;
  numero_economico: string;
  km_recorridos: number | null;
  diesel_consumido_pct: number | null;
  rendimiento_km_por_pct_diesel: number | null;
  consumo_valido: boolean;
};

export type KpiTrailerItem = {
  id_trailer: number;
  numero_economico: string;
  placas: string | null;
  km_recorridos: number;
  diesel_consumido_pct: number;
  rendimiento_km_por_pct_diesel: number | null;
  viajes: KpiTrailerViajeDetalle[];
};

export type KpiTrailersResponse = {
  periodo: { fecha_desde: string | null; fecha_hasta: string | null };
  total_km_recorridos: number;
  total_diesel_consumido_pct: number;
  rendimiento_promedio_km_por_pct_diesel: number | null;
  trailers: KpiTrailerItem[];
};

export type KpiClienteItem = {
  id_cliente: number;
  nombre: string;
  nombre_razon_social: string;
  viajes_terminados_semana: number;
  viajes_terminados_mes: number;
  viajes_en_espera: number;
};

export type KpiClientesResponse = {
  periodo: { fecha_desde: string | null; fecha_hasta: string | null };
  total_viajes_terminados_semana: number;
  total_viajes_terminados_mes: number;
  total_viajes_en_espera: number;
  series_semanales: KpiSerieItem[];
  series_mensuales: KpiSerieItem[];
  clientes: KpiClienteItem[];
};

export type KpiCatalogFilters = {
  fecha_inicio?: string;
  fecha_fin?: string;
  id_operador?: number;
  id_trailer?: number;
  id_cliente?: number;
  nombre_operador?: string;
  numero_economico?: string;
  nombre_cliente?: string;
};
