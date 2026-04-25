import { apiFetch } from "@/services/api-client";
import type {
  CreateEvidenciaPayload,
  EvidenciaResponse,
  PresignUploadRequest,
  PresignUploadResponse,
  TipoEvidencia
} from "@/types/evidencia";

export function getTiposEvidenciaRequest() {
  return apiFetch<TipoEvidencia[]>("/viajes/catalogos/tipos-evidencia");
}

export function getPresignedUrlRequest(payload: PresignUploadRequest) {
  return apiFetch<PresignUploadResponse>("/evidencias/presign-upload", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json"
    }
  });
}

export async function uploadFileToR2(uploadUrl: string, file: File) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": file.type || "application/octet-stream"
    },
    body: file
  });

  if (!response.ok) {
    throw new Error("No fue posible subir el archivo a almacenamiento");
  }
}

export function createEvidenciaRequest(viajeId: number, payload: CreateEvidenciaPayload) {
  return apiFetch<EvidenciaResponse>(`/viajes/${viajeId}/evidencias`, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json"
    }
  });
}
