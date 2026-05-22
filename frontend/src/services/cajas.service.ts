import { apiFetch } from "@/services/api-client";
import type { Caja, CreateCajaPayload, UpdateCajaPayload } from "@/types/caja";

export function getCajasRequest() {
  return apiFetch<Caja[]>("/cajas");
}

export function createCajaRequest(payload: CreateCajaPayload) {
  return apiFetch<Caja>("/cajas", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function updateCajaRequest(cajaId: number, payload: UpdateCajaPayload) {
  return apiFetch<Caja>(`/cajas/${cajaId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function deleteCajaRequest(cajaId: number) {
  return apiFetch<void>(`/cajas/${cajaId}`, {
    method: "DELETE"
  });
}
