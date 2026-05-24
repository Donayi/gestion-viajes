import { apiFetch } from "@/services/api-client";
import type { PushStatusResponse, PushSubscriptionPayload, PushTestResponse } from "@/types/push";

export function getPushStatusRequest() {
  return apiFetch<PushStatusResponse>("/push/status");
}

export function subscribePushRequest(payload: PushSubscriptionPayload) {
  return apiFetch("/push/subscribe", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function unsubscribePushRequest(endpoint: string) {
  return apiFetch<PushTestResponse>("/push/unsubscribe", {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ endpoint })
  });
}

export function sendPushTestRequest() {
  return apiFetch<PushTestResponse>("/push/test", {
    method: "POST"
  });
}
