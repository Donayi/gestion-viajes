import { apiFetch } from "@/services/api-client";
import type {
  CreateTelegramDestinatarioPayload,
  ProcesarNotificacionesResponse,
  TelegramDestinatario,
  TelegramTestResponse,
  UpdateTelegramDestinatarioPayload,
} from "@/types/telegram";

export function getTelegramDestinatariosRequest() {
  return apiFetch<TelegramDestinatario[]>("/telegram/destinatarios");
}

export function createTelegramDestinatarioRequest(payload: CreateTelegramDestinatarioPayload) {
  return apiFetch<TelegramDestinatario>("/telegram/destinatarios", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function updateTelegramDestinatarioRequest(
  destinatarioId: number,
  payload: UpdateTelegramDestinatarioPayload
) {
  return apiFetch<TelegramDestinatario>(`/telegram/destinatarios/${destinatarioId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function deleteTelegramDestinatarioRequest(destinatarioId: number) {
  return apiFetch<TelegramDestinatario>(`/telegram/destinatarios/${destinatarioId}`, {
    method: "DELETE",
  });
}

export function testTelegramDestinatarioRequest(destinatarioId: number) {
  return apiFetch<TelegramTestResponse>(`/telegram/test/${destinatarioId}`, {
    method: "POST",
  });
}

export function notificarAlertasPendientesRequest() {
  return apiFetch<ProcesarNotificacionesResponse>("/alertas/notificar-pendientes", {
    method: "POST",
  });
}
