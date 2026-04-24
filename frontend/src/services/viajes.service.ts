import { apiFetch } from "@/services/api-client";
import type {
  HistorialEstatusEnriched,
  ViajeAsignacionEnriched,
  ViajeDetail,
  ViajeListItem
} from "@/types/viaje";

export function getViajesEnrichedRequest() {
  return apiFetch<ViajeListItem[]>("/viajes/enriched");
}

export function getViajeDetailRequest(viajeId: number) {
  return apiFetch<ViajeDetail>(`/viajes/${viajeId}/detail`);
}

export function getViajeHistorialRequest(viajeId: number) {
  return apiFetch<HistorialEstatusEnriched[]>(
    `/viajes/${viajeId}/historial-estatus/enriched`
  );
}

export function getViajeAsignacionesRequest(viajeId: number) {
  return apiFetch<ViajeAsignacionEnriched[]>(
    `/viajes/${viajeId}/asignaciones/enriched`
  );
}
