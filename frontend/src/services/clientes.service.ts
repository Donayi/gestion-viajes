import { apiFetch } from "@/services/api-client";
import type { Cliente, CreateClientePayload, UpdateClientePayload } from "@/types/cliente";

export function getClientesRequest() {
  return apiFetch<Cliente[]>("/clientes");
}

export function createClienteRequest(payload: CreateClientePayload) {
  return apiFetch<Cliente>("/clientes", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function updateClienteRequest(clienteId: number, payload: UpdateClientePayload) {
  return apiFetch<Cliente>(`/clientes/${clienteId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function deleteClienteRequest(clienteId: number) {
  return apiFetch<void>(`/clientes/${clienteId}`, {
    method: "DELETE"
  });
}
