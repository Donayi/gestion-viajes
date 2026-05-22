import { apiFetch } from "@/services/api-client";
import type { CreateOperadorPayload, Operador, UpdateOperadorPayload } from "@/types/operador";

export function getOperadoresRequest() {
  return apiFetch<Operador[]>("/operadores");
}

export function createOperadorRequest(payload: CreateOperadorPayload) {
  return apiFetch<Operador>("/operadores", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function updateOperadorRequest(operadorId: number, payload: UpdateOperadorPayload) {
  return apiFetch<Operador>(`/operadores/${operadorId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function deleteOperadorRequest(operadorId: number) {
  return apiFetch<void>(`/operadores/${operadorId}`, {
    method: "DELETE"
  });
}
