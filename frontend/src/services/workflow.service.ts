import { apiFetch } from "@/services/api-client";
import type {
  CambioEstatusResponse,
  WorkflowActionPayload,
  ViajeDetail,
  WorkflowOperationalPayload
} from "@/types/viaje";

function postAction<TResponse>(path: string, payload?: WorkflowActionPayload) {
  return apiFetch<TResponse>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: payload ? JSON.stringify(payload) : undefined
  });
}

export function iniciarCargaRequest(viajeId: number, payload: WorkflowActionPayload) {
  return postAction<ViajeDetail>(`/viajes/${viajeId}/iniciar-carga`, payload);
}

export function iniciarViajeRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction<ViajeDetail>(`/viajes/${viajeId}/iniciar-viaje`, payload);
}

export function reiniciarViajeRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction<ViajeDetail>(`/viajes/${viajeId}/reiniciar-viaje`, payload);
}

export function marcarRetrasoRequest(viajeId: number, payload: WorkflowActionPayload) {
  return postAction<ViajeDetail>(`/viajes/${viajeId}/marcar-retraso`, payload);
}

export function ponerStandbyRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction<ViajeDetail>(`/viajes/${viajeId}/poner-standby`, payload);
}

export function finalizarViajeRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction<ViajeDetail>(`/viajes/${viajeId}/finalizar`, payload);
}

export function solicitarStandbyRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction<CambioEstatusResponse>(`/viajes/${viajeId}/solicitar-standby`, payload);
}

export function autorizarStandbyRequest(viajeId: number) {
  return postAction<ViajeDetail>(`/viajes/${viajeId}/autorizar-standby`);
}
