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
