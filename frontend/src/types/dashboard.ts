import type { AlertaNivel } from "@/types/alerta";
import type { KpiOperativoResumen } from "@/types/kpi";
import type { MantenimientoEntidadTipo, MantenimientoEstatus } from "@/types/mantenimiento";
import type { ViajeMapaItem } from "@/types/viaje";


export type DashboardStatusCount = {
  clave: string;
  nombre: string;
  total: number;
};

export type AdminDashboardViajesResumen = {
  total: number;
  activos: number;
  finalizados: number;
  standby: number;
  cancelados: number;
  sin_ubicacion: number;
  por_estatus: DashboardStatusCount[];
};

export type AdminDashboardDisponibilidadGrupo = {
  total: number;
  disponibles: number;
  ocupados: number;
  inactivos: number;
};

export type AdminDashboardDisponibilidadTrailers = {
  total: number;
  disponibles: number;
  ocupados: number;
  en_mantenimiento: number;
  inactivos: number;
};

export type AdminDashboardDisponibilidadCajas = {
  total: number;
  disponibles: number;
  ocupadas: number;
  en_mantenimiento: number;
  inactivas: number;
};

export type AdminDashboardDisponibilidad = {
  operadores: AdminDashboardDisponibilidadGrupo;
  trailers: AdminDashboardDisponibilidadTrailers;
  cajas: AdminDashboardDisponibilidadCajas;
};

export type AdminDashboardAlertItem = {
  id_alerta: number;
  tipo_alerta: string;
  entidad_tipo: string;
  entidad_id: number;
  mensaje: string;
  nivel: AlertaNivel;
  leida: boolean;
  created_at: string;
};

export type AdminDashboardAlertsSummary = {
  pendientes_total: number;
  criticas_no_leidas: number;
  items: AdminDashboardAlertItem[];
};

export type AdminDashboardMaintenanceItem = {
  id_mantenimiento: number;
  entidad_tipo: MantenimientoEntidadTipo;
  entidad_id: number | null;
  tipo_mantenimiento: string;
  estatus: MantenimientoEstatus;
  fecha_inicio: string;
  fecha_mantenimiento: string | null;
  fecha_proximo_mantenimiento: string | null;
  descripcion: string;
  entidad: {
    id: number;
    etiqueta: string;
    subtitulo: string | null;
  };
};

export type AdminDashboardMaintenanceSummary = {
  abiertos_total: number;
  en_proceso_total: number;
  proximos_total: number;
  items: AdminDashboardMaintenanceItem[];
};

export type AdminDashboardMapSummary = {
  total_con_ubicacion: number;
  total_sin_ubicacion: number;
  items: ViajeMapaItem[];
};

export type AdminDashboardResponse = {
  generated_at: string;
  viajes_resumen: AdminDashboardViajesResumen;
  kpis_operativos: KpiOperativoResumen;
  disponibilidad: AdminDashboardDisponibilidad;
  alertas: AdminDashboardAlertsSummary;
  mantenimientos: AdminDashboardMaintenanceSummary;
  mapa: AdminDashboardMapSummary;
};
