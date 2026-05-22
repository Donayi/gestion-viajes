import { apiFetch } from "@/services/api-client";
import type { CreateTrailerPayload, Trailer, UpdateTrailerPayload } from "@/types/trailer";

export function getTrailersRequest() {
  return apiFetch<Trailer[]>("/trailers");
}

export function createTrailerRequest(payload: CreateTrailerPayload) {
  return apiFetch<Trailer>("/trailers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function updateTrailerRequest(trailerId: number, payload: UpdateTrailerPayload) {
  return apiFetch<Trailer>(`/trailers/${trailerId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function deleteTrailerRequest(trailerId: number) {
  return apiFetch<void>(`/trailers/${trailerId}`, {
    method: "DELETE"
  });
}
