import { apiFetch } from "@/services/api-client";
import type { AlertaRecord, GenerarAlertasResponse } from "@/types/alerta";

export function getAlertasRequest(params?: { tipo_alerta?: string; nivel?: string }) {
  const search = new URLSearchParams();
  if (params?.tipo_alerta) {
    search.set("tipo_alerta", params.tipo_alerta);
  }
  if (params?.nivel) {
    search.set("nivel", params.nivel);
  }
  const query = search.toString();
  return apiFetch<AlertaRecord[]>(query ? `/alertas?${query}` : "/alertas");
}

export function generarAlertasRequest() {
  return apiFetch<GenerarAlertasResponse>("/alertas/generar", {
    method: "POST",
  });
}

export function marcarAlertaLeidaRequest(alertaId: number) {
  return apiFetch<AlertaRecord>(`/alertas/${alertaId}/leer`, {
    method: "PATCH",
  });
}
