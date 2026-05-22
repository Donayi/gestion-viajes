import { apiFetch } from "@/services/api-client";
import type {
  CajaDisponible,
  DisponibilidadResumen,
  EventoOperativoViaje,
  HistorialEstatusEnriched,
  OperadorDisponible,
  TrailerDisponible,
  ViajeAsignacionCreatePayload,
  ViajeAsignacionEnriched,
  ViajeAsignacionRecord,
  ViajeCreatePayload,
  ViajeDetail,
  EventoOperativoViajeUpdatePayload,
  ViajeListItem,
  ViajeMapaItem,
  ViajeReasignacionCreatePayload,
  ViajeRecord,
  ViajeUpdatePayload
} from "@/types/viaje";

export function getViajesEnrichedRequest() {
  return apiFetch<ViajeListItem[]>("/viajes/enriched");
}

export function getViajesMapaRequest(filters?: {
  estatus?: string[];
  incluirFinalizados?: boolean;
  incluirCancelados?: boolean;
}) {
  const params = new URLSearchParams();

  filters?.estatus?.forEach((clave) => params.append("estatus", clave));

  if (filters?.incluirFinalizados !== undefined) {
    params.set("incluir_finalizados", String(filters.incluirFinalizados));
  }

  if (filters?.incluirCancelados !== undefined) {
    params.set("incluir_cancelados", String(filters.incluirCancelados));
  }

  const query = params.toString();
  return apiFetch<ViajeMapaItem[]>(`/viajes/mapa${query ? `?${query}` : ""}`);
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

export function getViajeEventosOperativosRequest(viajeId: number) {
  return apiFetch<EventoOperativoViaje[]>(`/viajes/${viajeId}/eventos-operativos`);
}

export function updateEventoOperativoRequest(
  viajeId: number,
  eventoId: number,
  payload: EventoOperativoViajeUpdatePayload
) {
  return apiFetch<EventoOperativoViaje>(`/viajes/${viajeId}/eventos-operativos/${eventoId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function createViajeRequest(payload: ViajeCreatePayload, createdBy?: number | null) {
  const query = createdBy ? `?created_by=${createdBy}` : "";
  return apiFetch<ViajeRecord>(`/viajes${query}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function updateViajeRequest(viajeId: number, payload: ViajeUpdatePayload) {
  return apiFetch<ViajeRecord>(`/viajes/${viajeId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function asignarViajeRequest(viajeId: number, payload: ViajeAsignacionCreatePayload) {
  return apiFetch<ViajeAsignacionRecord>(`/viajes/${viajeId}/asignar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function reasignarViajeRequest(
  viajeId: number,
  payload: ViajeReasignacionCreatePayload
) {
  return apiFetch<ViajeAsignacionRecord>(`/viajes/${viajeId}/reasignar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function getOperadoresDisponiblesRequest() {
  return apiFetch<OperadorDisponible[]>("/viajes/disponibilidad/operadores");
}

export function getTrailersDisponiblesRequest() {
  return apiFetch<TrailerDisponible[]>("/viajes/disponibilidad/trailers");
}

export function getCajasDisponiblesRequest() {
  return apiFetch<CajaDisponible[]>("/viajes/disponibilidad/cajas");
}

export function getDisponibilidadResumenRequest() {
  return apiFetch<DisponibilidadResumen>("/viajes/disponibilidad/resumen");
}
