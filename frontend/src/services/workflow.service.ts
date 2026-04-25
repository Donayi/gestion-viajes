import { apiFetch } from "@/services/api-client";
import type {
  ViajeComentarioAccion,
  ViajeDetail,
  WorkflowOperationalPayload
} from "@/types/viaje";

function postAction(path: string, payload: ViajeComentarioAccion | WorkflowOperationalPayload) {
  return apiFetch<ViajeDetail>(path, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json"
    }
  });
}

export function iniciarCargaRequest(viajeId: number, payload: ViajeComentarioAccion) {
  return postAction(`/viajes/${viajeId}/iniciar-carga`, payload);
}

export function iniciarViajeRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction(`/viajes/${viajeId}/iniciar-viaje`, payload);
}

export function marcarRetrasoRequest(viajeId: number, payload: ViajeComentarioAccion) {
  return postAction(`/viajes/${viajeId}/marcar-retraso`, payload);
}

export function ponerStandbyRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction(`/viajes/${viajeId}/poner-standby`, payload);
}

export function finalizarViajeRequest(viajeId: number, payload: WorkflowOperationalPayload) {
  return postAction(`/viajes/${viajeId}/finalizar`, payload);
}
