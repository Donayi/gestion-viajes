import { apiFetch } from "@/services/api-client";
import type {
  KpiCatalogFilters,
  KpiClientesResponse,
  KpiOperadoresResponse,
  KpiOperativoDashboard,
  KpiOperativoFilters,
  KpiTrailersResponse,
} from "@/types/kpi";

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

function buildCatalogFilters(filters: KpiCatalogFilters = {}, entityKey?: "id_operador" | "id_trailer" | "id_cliente") {
  const searchParams = new URLSearchParams();

  if (filters.fecha_inicio) searchParams.set("fecha_inicio", filters.fecha_inicio);
  if (filters.fecha_fin) searchParams.set("fecha_fin", filters.fecha_fin);
  if (entityKey === "id_operador" && typeof filters.id_operador === "number") {
    searchParams.set("id_operador", String(filters.id_operador));
  }
  if (entityKey === "id_operador" && filters.nombre_operador) {
    searchParams.set("nombre_operador", filters.nombre_operador);
  }
  if (entityKey === "id_trailer" && typeof filters.id_trailer === "number") {
    searchParams.set("id_trailer", String(filters.id_trailer));
  }
  if (entityKey === "id_trailer" && filters.numero_economico) {
    searchParams.set("numero_economico", filters.numero_economico);
  }
  if (entityKey === "id_cliente" && typeof filters.id_cliente === "number") {
    searchParams.set("id_cliente", String(filters.id_cliente));
  }
  if (entityKey === "id_cliente" && filters.nombre_cliente) {
    searchParams.set("nombre_cliente", filters.nombre_cliente);
  }

  return searchParams.toString();
}

export function getKpisOperadoresRequest(filters: KpiCatalogFilters = {}) {
  const query = buildCatalogFilters(filters, "id_operador");
  return apiFetch<KpiOperadoresResponse>(`/kpis/operadores${query ? `?${query}` : ""}`);
}

export function getKpisTrailersRequest(filters: KpiCatalogFilters = {}) {
  const query = buildCatalogFilters(filters, "id_trailer");
  return apiFetch<KpiTrailersResponse>(`/kpis/trailers${query ? `?${query}` : ""}`);
}

export function getKpisClientesRequest(filters: KpiCatalogFilters = {}) {
  const query = buildCatalogFilters(filters, "id_cliente");
  return apiFetch<KpiClientesResponse>(`/kpis/clientes${query ? `?${query}` : ""}`);
}
