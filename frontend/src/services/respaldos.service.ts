import { apiDownload, apiFetch } from "@/services/api-client";
import type { ListaRespaldosAdministrativos, RespaldoAdministrativo } from "@/types/respaldo";

export function getRespaldosRequest() {
  return apiFetch<ListaRespaldosAdministrativos>("/respaldos?page=1&page_size=100");
}

export function generateRespaldoRequest() {
  return apiFetch<RespaldoAdministrativo>("/respaldos/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function downloadRespaldoRequest(respaldoId: string) {
  return apiDownload(`/respaldos/${encodeURIComponent(respaldoId)}/descarga`);
}
