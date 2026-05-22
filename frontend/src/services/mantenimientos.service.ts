import { apiFetch } from "@/services/api-client";
import type {
  CreateMantenimientoPayload,
  CreateMantenimientoArchivoPayload,
  CreateMantenimientoChecklistEvidenciaPayload,
  MantenimientoCambioEstadoPayload,
  MantenimientoArchivoRecord,
  MantenimientoChecklistEvidenciaRecord,
  MantenimientoEntidadTipo,
  MantenimientoChecklistItem,
  MantenimientoRecursosDisponibles,
  MantenimientoRecord,
  UpdateMantenimientoArchivoPayload,
  UpdateMantenimientoChecklistEvidenciaPayload,
  UpdateMantenimientoChecklistItemPayload,
  UpdateMantenimientoPayload,
} from "@/types/mantenimiento";

export function getMantenimientosRequest(params?: {
  entidad_tipo?: MantenimientoEntidadTipo;
  estatus?: string;
}) {
  const search = new URLSearchParams();
  if (params?.entidad_tipo) {
    search.set("entidad_tipo", params.entidad_tipo);
  }
  if (params?.estatus) {
    search.set("estatus", params.estatus);
  }
  const query = search.toString();
  return apiFetch<MantenimientoRecord[]>(query ? `/mantenimientos?${query}` : "/mantenimientos");
}

export function getMantenimientoRecursosDisponiblesRequest() {
  return apiFetch<MantenimientoRecursosDisponibles>("/mantenimientos/recursos-disponibles");
}

export function getMantenimientoRequest(mantenimientoId: number) {
  return apiFetch<MantenimientoRecord>(`/mantenimientos/${mantenimientoId}`);
}

export function createMantenimientoRequest(payload: CreateMantenimientoPayload) {
  return apiFetch<MantenimientoRecord>("/mantenimientos", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function updateMantenimientoRequest(
  mantenimientoId: number,
  payload: UpdateMantenimientoPayload
) {
  return apiFetch<MantenimientoRecord>(`/mantenimientos/${mantenimientoId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function cerrarMantenimientoRequest(
  mantenimientoId: number,
  payload: MantenimientoCambioEstadoPayload = {}
) {
  return apiFetch<MantenimientoRecord>(`/mantenimientos/${mantenimientoId}/cerrar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function cancelarMantenimientoRequest(
  mantenimientoId: number,
  payload: MantenimientoCambioEstadoPayload = {}
) {
  return apiFetch<MantenimientoRecord>(`/mantenimientos/${mantenimientoId}/cancelar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function updateMantenimientoChecklistItemRequest(
  mantenimientoId: number,
  itemId: number,
  payload: UpdateMantenimientoChecklistItemPayload
) {
  return apiFetch<MantenimientoChecklistItem>(
    `/mantenimientos/${mantenimientoId}/checklist/${itemId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );
}

export function getMantenimientoArchivosRequest(mantenimientoId: number, soloActivos = false) {
  const query = soloActivos ? "?solo_activos=true" : "";
  return apiFetch<MantenimientoArchivoRecord[]>(`/mantenimientos/${mantenimientoId}/archivos${query}`);
}

export function createMantenimientoArchivoRequest(
  mantenimientoId: number,
  payload: CreateMantenimientoArchivoPayload
) {
  return apiFetch<MantenimientoArchivoRecord>(`/mantenimientos/${mantenimientoId}/archivos`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function updateMantenimientoArchivoRequest(
  mantenimientoId: number,
  mantenimientoArchivoId: number,
  payload: UpdateMantenimientoArchivoPayload
) {
  return apiFetch<MantenimientoArchivoRecord>(
    `/mantenimientos/${mantenimientoId}/archivos/${mantenimientoArchivoId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );
}

export function deleteMantenimientoArchivoRequest(
  mantenimientoId: number,
  mantenimientoArchivoId: number
) {
  return apiFetch<MantenimientoArchivoRecord>(
    `/mantenimientos/${mantenimientoId}/archivos/${mantenimientoArchivoId}`,
    {
      method: "DELETE",
    }
  );
}

export function getChecklistItemEvidenciasRequest(
  mantenimientoId: number,
  itemId: number,
  soloActivos = false
) {
  const query = soloActivos ? "?solo_activos=true" : "";
  return apiFetch<MantenimientoChecklistEvidenciaRecord[]>(
    `/mantenimientos/${mantenimientoId}/checklist/${itemId}/evidencias${query}`
  );
}

export function createChecklistItemEvidenciaRequest(
  mantenimientoId: number,
  itemId: number,
  payload: CreateMantenimientoChecklistEvidenciaPayload
) {
  return apiFetch<MantenimientoChecklistEvidenciaRecord>(
    `/mantenimientos/${mantenimientoId}/checklist/${itemId}/evidencias`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );
}

export function updateChecklistItemEvidenciaRequest(
  mantenimientoId: number,
  itemId: number,
  checklistEvidenciaId: number,
  payload: UpdateMantenimientoChecklistEvidenciaPayload
) {
  return apiFetch<MantenimientoChecklistEvidenciaRecord>(
    `/mantenimientos/${mantenimientoId}/checklist/${itemId}/evidencias/${checklistEvidenciaId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );
}

export function deleteChecklistItemEvidenciaRequest(
  mantenimientoId: number,
  itemId: number,
  checklistEvidenciaId: number
) {
  return apiFetch<MantenimientoChecklistEvidenciaRecord>(
    `/mantenimientos/${mantenimientoId}/checklist/${itemId}/evidencias/${checklistEvidenciaId}`,
    {
      method: "DELETE",
    }
  );
}
