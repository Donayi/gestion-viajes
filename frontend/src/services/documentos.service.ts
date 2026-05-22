import { apiFetch } from "@/services/api-client";
import type {
  CreateDocumentoPayload,
  DocumentoEntidadTipo,
  DocumentoRecord,
  TipoDocumento,
  UpdateDocumentoPayload,
} from "@/types/documento";

export function getTiposDocumentoRequest(aplicaA?: DocumentoEntidadTipo) {
  const query = aplicaA ? `?aplica_a=${aplicaA}` : "";
  return apiFetch<TipoDocumento[]>(`/documentos/tipos${query}`);
}

export function getDocumentosRequest(entidadTipo?: DocumentoEntidadTipo, entidadId?: number) {
  const params = new URLSearchParams();
  if (entidadTipo) params.set("entidad_tipo", entidadTipo);
  if (typeof entidadId === "number") params.set("entidad_id", String(entidadId));
  params.set("solo_activos", "false");
  const query = params.toString();
  return apiFetch<DocumentoRecord[]>(`/documentos${query ? `?${query}` : ""}`);
}

export function createDocumentoRequest(payload: CreateDocumentoPayload) {
  return apiFetch<DocumentoRecord>("/documentos", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function updateDocumentoRequest(documentoId: number, payload: UpdateDocumentoPayload) {
  return apiFetch<DocumentoRecord>(`/documentos/${documentoId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function deleteDocumentoRequest(documentoId: number) {
  return apiFetch<DocumentoRecord>(`/documentos/${documentoId}`, {
    method: "DELETE",
  });
}
