import { apiFetch } from "@/services/api-client";
import type { KpiOperativoDashboard, KpiOperativoFilters } from "@/types/kpi";

export function getKpisOperativosRequest(filters: KpiOperativoFilters = {}) {
  const searchParams = new URLSearchParams();

  if (filters.fecha_desde) searchParams.set("fecha_desde", filters.fecha_desde);
  if (filters.fecha_hasta) searchParams.set("fecha_hasta", filters.fecha_hasta);
  if (typeof filters.id_operador === "number") searchParams.set("id_operador", String(filters.id_operador));
  if (typeof filters.id_cliente === "number") searchParams.set("id_cliente", String(filters.id_cliente));
  if (typeof filters.id_estatus === "number") searchParams.set("id_estatus", String(filters.id_estatus));
  if (filters.solo_completos) searchParams.set("solo_completos", "true");

  const query = searchParams.toString();
  return apiFetch<KpiOperativoDashboard>(`/viajes/kpis-operativos${query ? `?${query}` : ""}`);
}
