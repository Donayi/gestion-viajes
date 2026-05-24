"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AdminEmptyState } from "@/components/admin/admin-empty-state";
import { AdminModal } from "@/components/admin/admin-modal";
import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AdminTableShell } from "@/components/admin/admin-table-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EvidenceFilePicker } from "@/components/ui/evidence-file-picker";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { Textarea } from "@/components/ui/textarea";
import { useSession } from "@/hooks/use-session";
import { cn } from "@/lib/cn";
import {
  prepareEvidenceFile,
  revokePreparedEvidenceFile,
  type PreparedEvidenceFile,
} from "@/lib/evidence-files";
import { isAdmin, isMantenimiento } from "@/lib/permissions";
import { ApiError } from "@/services/api-client";
import { getPresignedUrlRequest, uploadFileToR2 } from "@/services/evidencias.service";
import {
  cancelarMantenimientoRequest,
  cerrarMantenimientoRequest,
  createChecklistItemEvidenciaRequest,
  createMantenimientoRequest,
  createMantenimientoArchivoRequest,
  deleteChecklistItemEvidenciaRequest,
  deleteMantenimientoArchivoRequest,
  getMantenimientoRecursosDisponiblesRequest,
  getMantenimientosRequest,
  updateChecklistItemEvidenciaRequest,
  updateMantenimientoArchivoRequest,
  updateMantenimientoChecklistItemRequest,
  updateMantenimientoRequest,
} from "@/services/mantenimientos.service";
import { getCajasRequest } from "@/services/cajas.service";
import { getTrailersRequest } from "@/services/trailers.service";
import { getDisponibilidadResumenRequest } from "@/services/viajes.service";
import type { Caja } from "@/types/caja";
import type {
  CreateMantenimientoPayload,
  MantenimientoArchivoRecord,
  MantenimientoArchivoTipo,
  MantenimientoCajaDisponible,
  MantenimientoChecklistEvidenciaRecord,
  MantenimientoEntidadTipo,
  MantenimientoEstatus,
  MantenimientoRecord,
  MantenimientoTrailerDisponible,
  MantenimientoTipo,
} from "@/types/mantenimiento";
import type { Trailer } from "@/types/trailer";
import type { DisponibilidadResumen } from "@/types/viaje";

type MantenimientoFilter = "TODOS" | MantenimientoEstatus;
type EntityFilter = "TODOS" | MantenimientoEntidadTipo;

type CreateFormState = {
  entidad_tipo: MantenimientoEntidadTipo;
  entidad_id: string;
  tipo_mantenimiento: MantenimientoTipo;
  fecha_mantenimiento: string;
  fecha_proximo_mantenimiento: string;
  kilometraje: string;
  descripcion: string;
  observaciones: string;
};

type DetailFormState = {
  tipo_mantenimiento: MantenimientoTipo;
  estatus: MantenimientoEstatus;
  fecha_mantenimiento: string;
  fecha_proximo_mantenimiento: string;
  kilometraje: string;
  descripcion: string;
  observaciones: string;
};

type ArchivoFormState = {
  tipo_archivo: MantenimientoArchivoTipo;
  comentario: string;
  file: File | null;
};

type ChecklistEvidenceFormState = {
  comentario: string;
  file: PreparedEvidenceFile | null;
};

type MantenimientosWorkbenchProps = {
  variant?: "admin" | "maintenance";
  startCreate?: boolean;
  focusMaintenanceId?: number | null;
  maintenanceView?: "split" | "list" | "create" | "detail";
};

const statusOptions: Array<{ key: MantenimientoFilter; label: string }> = [
  { key: "TODOS", label: "Todos" },
  { key: "ABIERTO", label: "Abiertos" },
  { key: "EN_PROCESO", label: "En proceso" },
  { key: "CERRADO", label: "Cerrados" },
  { key: "CANCELADO", label: "Cancelados" },
];

const entityOptions: Array<{ key: EntityFilter; label: string }> = [
  { key: "TODOS", label: "Todos" },
  { key: "TRAILER", label: "Tráilers" },
  { key: "CAJA", label: "Cajas" },
];

const maintenanceTypeOptions: MantenimientoTipo[] = ["PREVENTIVO", "CORRECTIVO", "REPARACION"];
const maintenanceFileTypeOptions: Array<{ value: MantenimientoArchivoTipo; label: string }> = [
  { value: "FOTO_ANTES", label: "Foto antes" },
  { value: "FOTO_DESPUES", label: "Foto después" },
  { value: "FACTURA", label: "Factura" },
  { value: "DIAGNOSTICO", label: "Diagnóstico" },
  { value: "OTRO", label: "Otro" },
];
const activeStatuses = new Set<MantenimientoEstatus>(["ABIERTO", "EN_PROCESO"]);

const initialCreateForm: CreateFormState = {
  entidad_tipo: "TRAILER",
  entidad_id: "",
  tipo_mantenimiento: "PREVENTIVO",
  fecha_mantenimiento: "",
  fecha_proximo_mantenimiento: "",
  kilometraje: "",
  descripcion: "",
  observaciones: "",
};

const initialArchivoForm: ArchivoFormState = {
  tipo_archivo: "FOTO_ANTES",
  comentario: "",
  file: null,
};

const initialChecklistEvidenceForm: ChecklistEvidenceFormState = {
  comentario: "",
  file: null,
};

function buildDetailForm(mantenimiento: MantenimientoRecord): DetailFormState {
  return {
    tipo_mantenimiento: mantenimiento.tipo_mantenimiento,
    estatus: mantenimiento.estatus,
    fecha_mantenimiento: mantenimiento.fecha_mantenimiento ?? "",
    fecha_proximo_mantenimiento: mantenimiento.fecha_proximo_mantenimiento ?? "",
    kilometraje:
      mantenimiento.kilometraje !== null && mantenimiento.kilometraje !== undefined
        ? String(mantenimiento.kilometraje)
        : "",
    descripcion: mantenimiento.descripcion,
    observaciones: mantenimiento.observaciones ?? "",
  };
}

function normalize(text: string | null | undefined) {
  return (text ?? "").toLowerCase();
}

function getStatusBadgeClass(estatus: MantenimientoEstatus) {
  if (estatus === "ABIERTO") return "border-amber-200 bg-amber-50 text-amber-700";
  if (estatus === "EN_PROCESO") return "border-sky-200 bg-sky-50 text-sky-700";
  if (estatus === "CERRADO") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  return "border-slate-200 bg-slate-100 text-slate-600";
}

function isImageFile(contentType: string | null | undefined) {
  return (contentType ?? "").startsWith("image/");
}

function isPdfFile(contentType: string | null | undefined) {
  return (contentType ?? "").includes("pdf");
}

function getChecklistCompletionWarning(mantenimiento: MantenimientoRecord | null) {
  if (!mantenimiento) {
    return null;
  }

  const incomplete = mantenimiento.checklist_items.filter((item) => !item.completado).length;
  const withoutEvidence = mantenimiento.checklist_items.filter(
    (item) => item.evidencias.filter((evidencia) => evidencia.activo).length === 0
  ).length;

  if (incomplete === 0 && withoutEvidence === 0) {
    return null;
  }

  return {
    incomplete,
    withoutEvidence,
  };
}

function getTrailerAvailabilityMap(summary: DisponibilidadResumen | null) {
  return new Map((summary?.trailers ?? []).map((item) => [item.id_trailer, item]));
}

function getCajaAvailabilityMap(summary: DisponibilidadResumen | null) {
  return new Map((summary?.cajas ?? []).map((item) => [item.id_caja, item]));
}

export function MantenimientosWorkbench({
  variant = "admin",
  startCreate = false,
  focusMaintenanceId = null,
  maintenanceView = "split",
}: MantenimientosWorkbenchProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useSession();
  const maintenanceMode = variant === "maintenance";
  const maintenanceUser = isMantenimiento(user);
  const adminUser = isAdmin(user);
  const canCreate = maintenanceMode && maintenanceUser;
  const canOperate = maintenanceMode && maintenanceUser;
  const listBasePath = maintenanceMode ? "/mantenimiento" : "/admin/mantenimientos";
  const detailBasePath = maintenanceMode ? "/mantenimiento" : "/admin/mantenimientos";
  const maintenanceListOnly = maintenanceMode && maintenanceView === "list";
  const maintenanceCreateOnly = maintenanceMode && maintenanceView === "create";
  const maintenanceDetailOnly = maintenanceMode && maintenanceView === "detail";
  const maintenanceSplitView = maintenanceMode && maintenanceView === "split";
  const adminListOnly = !maintenanceMode && maintenanceView === "list";
  const adminDetailOnly = !maintenanceMode && maintenanceView === "detail";
  const detailOnlyView = maintenanceDetailOnly || adminDetailOnly;
  const listOnlyView = maintenanceListOnly || adminListOnly;
  const showListPanel = !detailOnlyView;
  const showDetailPanel = !listOnlyView;

  const [mantenimientos, setMantenimientos] = useState<MantenimientoRecord[]>([]);
  const [trailers, setTrailers] = useState<Trailer[]>([]);
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [maintenanceTrailers, setMaintenanceTrailers] = useState<MantenimientoTrailerDisponible[]>([]);
  const [maintenanceCajas, setMaintenanceCajas] = useState<MantenimientoCajaDisponible[]>([]);
  const [summary, setSummary] = useState<DisponibilidadResumen | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<MantenimientoFilter>("TODOS");
  const [entityFilter, setEntityFilter] = useState<EntityFilter>("TODOS");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<CreateFormState>(initialCreateForm);
  const [selectedMaintenanceId, setSelectedMaintenanceId] = useState<number | null>(null);
  const [detailForm, setDetailForm] = useState<DetailFormState | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [savingDetail, setSavingDetail] = useState(false);
  const [actionBusy, setActionBusy] = useState<"cerrar" | "cancelar" | null>(null);
  const [checklistSavingId, setChecklistSavingId] = useState<number | null>(null);
  const [checklistDrafts, setChecklistDrafts] = useState<Record<number, string>>({});
  const [archivoModalOpen, setArchivoModalOpen] = useState(false);
  const [archivoForm, setArchivoForm] = useState<ArchivoFormState>(initialArchivoForm);
  const [archivoError, setArchivoError] = useState<string | null>(null);
  const [archivoSubmitting, setArchivoSubmitting] = useState(false);
  const [editingArchivo, setEditingArchivo] = useState<MantenimientoArchivoRecord | null>(null);
  const [checklistEvidenceModalOpen, setChecklistEvidenceModalOpen] = useState(false);
  const [selectedChecklistItemForEvidence, setSelectedChecklistItemForEvidence] = useState<number | null>(null);
  const [editingChecklistEvidence, setEditingChecklistEvidence] =
    useState<MantenimientoChecklistEvidenciaRecord | null>(null);
  const [checklistEvidenceForm, setChecklistEvidenceForm] = useState<ChecklistEvidenceFormState>(
    initialChecklistEvidenceForm
  );
  const [checklistEvidenceError, setChecklistEvidenceError] = useState<string | null>(null);
  const [checklistEvidenceSubmitting, setChecklistEvidenceSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const mantenimientosData = await getMantenimientosRequest();
      setMantenimientos(mantenimientosData);
      if (maintenanceMode) {
        const resources = await getMantenimientoRecursosDisponiblesRequest();
        setMaintenanceTrailers(resources.trailers);
        setMaintenanceCajas(resources.cajas);
        setTrailers([]);
        setCajas([]);
        setSummary(null);
      } else {
        const [trailersData, cajasData, summaryData] = await Promise.all([
          getTrailersRequest(),
          getCajasRequest(),
          getDisponibilidadResumenRequest(),
        ]);
        setTrailers(trailersData);
        setCajas(cajasData);
        setSummary(summaryData);
        setMaintenanceTrailers([]);
        setMaintenanceCajas([]);
      }
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cargar los mantenimientos"
      );
    } finally {
      setLoading(false);
    }
  }, [maintenanceMode]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    return () => {
      revokePreparedEvidenceFile(checklistEvidenceForm.file);
    };
  }, [checklistEvidenceForm.file]);

  const scopedMantenimientos = useMemo(() => {
    if (!maintenanceMode || !user) {
      return mantenimientos;
    }
    return mantenimientos.filter((mantenimiento) => mantenimiento.created_by === user.id_usuario);
  }, [maintenanceMode, mantenimientos, user]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return scopedMantenimientos.filter((mantenimiento) => {
      if (statusFilter !== "TODOS" && mantenimiento.estatus !== statusFilter) {
        return false;
      }
      if (entityFilter !== "TODOS" && mantenimiento.entidad_tipo !== entityFilter) {
        return false;
      }
      if (!query) {
        return true;
      }

      const haystack = [
        mantenimiento.entidad_tipo,
        mantenimiento.entidad.etiqueta,
        mantenimiento.entidad.subtitulo,
        mantenimiento.tipo_mantenimiento,
        mantenimiento.estatus,
        mantenimiento.descripcion,
        mantenimiento.observaciones,
      ]
        .map(normalize)
        .join(" ");

      return haystack.includes(query);
    });
  }, [entityFilter, scopedMantenimientos, search, statusFilter]);

  useEffect(() => {
    if (detailOnlyView) {
      if (focusMaintenanceId === null) {
        setSelectedMaintenanceId(null);
        setDetailForm(null);
        setChecklistDrafts({});
        return;
      }

      const focused = filtered.find((mantenimiento) => mantenimiento.id_mantenimiento === focusMaintenanceId);
      if (!focused) {
        setSelectedMaintenanceId(null);
        setDetailForm(null);
        setChecklistDrafts({});
        return;
      }

      setSelectedMaintenanceId(focused.id_mantenimiento);
      setDetailForm(buildDetailForm(focused));
      setChecklistDrafts(
        Object.fromEntries(
          focused.checklist_items.map((item) => [item.id_item, item.observaciones ?? ""])
        )
      );
      return;
    }

    if (filtered.length === 0) {
      setSelectedMaintenanceId(null);
      setDetailForm(null);
      setChecklistDrafts({});
      return;
    }

    const selectedStillVisible = filtered.some(
      (mantenimiento) => mantenimiento.id_mantenimiento === selectedMaintenanceId
    );
    if (!selectedStillVisible) {
      const first = filtered[0];
      setSelectedMaintenanceId(first.id_mantenimiento);
      setDetailForm(buildDetailForm(first));
      setChecklistDrafts(
        Object.fromEntries(
          first.checklist_items.map((item) => [item.id_item, item.observaciones ?? ""])
        )
      );
    }
  }, [detailOnlyView, filtered, focusMaintenanceId, selectedMaintenanceId]);

  const selectedMaintenance = useMemo(
    () =>
      filtered.find((mantenimiento) => mantenimiento.id_mantenimiento === selectedMaintenanceId) ?? null,
    [filtered, selectedMaintenanceId]
  );
  const checklistWarning = useMemo(
    () => getChecklistCompletionWarning(selectedMaintenance),
    [selectedMaintenance]
  );
  const canCloseMaintenance = useMemo(
    () =>
      Boolean(selectedMaintenance) &&
      activeStatuses.has(selectedMaintenance?.estatus ?? "CERRADO") &&
      (canOperate || (!maintenanceMode && adminUser)),
    [adminUser, canOperate, maintenanceMode, selectedMaintenance]
  );
  const canCancelMaintenance = useMemo(
    () =>
      Boolean(selectedMaintenance) &&
      activeStatuses.has(selectedMaintenance?.estatus ?? "CERRADO") &&
      !maintenanceMode &&
      adminUser,
    [adminUser, maintenanceMode, selectedMaintenance]
  );

  useEffect(() => {
    if (!selectedMaintenance) {
      return;
    }
    setDetailForm(buildDetailForm(selectedMaintenance));
    setChecklistDrafts(
      Object.fromEntries(
        selectedMaintenance.checklist_items.map((item) => [item.id_item, item.observaciones ?? ""])
      )
    );
  }, [selectedMaintenance?.id_mantenimiento]); // eslint-disable-line react-hooks/exhaustive-deps

  const trailerAvailability = useMemo(() => getTrailerAvailabilityMap(summary), [summary]);
  const cajaAvailability = useMemo(() => getCajaAvailabilityMap(summary), [summary]);

  const availableTrailers = useMemo(
    () => {
      if (maintenanceMode) {
        return maintenanceTrailers
          .map((item) => ({
            id_trailer: item.id_trailer,
            numero_economico: item.numero_economico,
            placas: item.placas,
          }))
          .sort((a, b) => a.numero_economico.localeCompare(b.numero_economico));
      }

      return trailers
        .filter((trailer) => {
          const availability = trailerAvailability.get(trailer.id_trailer);
          return trailer.activo && availability?.disponible;
        })
        .sort((a, b) => a.numero_economico.localeCompare(b.numero_economico));
    },
    [maintenanceMode, maintenanceTrailers, trailerAvailability, trailers]
  );

  const availableCajas = useMemo(
    () => {
      if (maintenanceMode) {
        return maintenanceCajas
          .map((item) => ({
            id_caja: item.id_caja,
            numero_economico: item.numero_economico,
            placas: item.placas,
          }))
          .sort((a, b) => (a.numero_economico ?? a.placas).localeCompare(b.numero_economico ?? b.placas));
      }

      return cajas
        .filter((caja) => {
          const availability = cajaAvailability.get(caja.id_caja);
          return caja.activo && availability?.disponible;
        })
        .sort((a, b) => (a.numero_economico ?? a.placas).localeCompare(b.numero_economico ?? b.placas));
    },
    [cajaAvailability, cajas, maintenanceCajas, maintenanceMode]
  );

  const createFormContent = (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-700">Entidad</span>
          <select
            className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
            value={createForm.entidad_tipo}
            onChange={(event) =>
              setCreateForm((current) => ({
                ...current,
                entidad_tipo: event.target.value as MantenimientoEntidadTipo,
                entidad_id: "",
              }))
            }
          >
            <option value="TRAILER">Tráiler</option>
            <option value="CAJA">Caja</option>
          </select>
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-700">Recurso</span>
          <select
            className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
            value={createForm.entidad_id}
            onChange={(event) =>
              setCreateForm((current) => ({ ...current, entidad_id: event.target.value }))
            }
          >
            <option value="">Selecciona un recurso</option>
            {createForm.entidad_tipo === "TRAILER"
              ? availableTrailers.map((item) => (
                  <option key={item.id_trailer} value={item.id_trailer}>
                    {item.numero_economico} · {item.placas}
                  </option>
                ))
              : availableCajas.map((item) => (
                  <option key={item.id_caja} value={item.id_caja}>
                    {item.numero_economico ?? item.placas} · {item.placas}
                  </option>
                ))}
          </select>
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-700">Tipo de mantenimiento</span>
          <select
            className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
            value={createForm.tipo_mantenimiento}
            onChange={(event) =>
              setCreateForm((current) => ({
                ...current,
                tipo_mantenimiento: event.target.value as MantenimientoTipo,
              }))
            }
          >
            {maintenanceTypeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <Input
          label="Fecha del mantenimiento"
          type="date"
          value={createForm.fecha_mantenimiento}
          onChange={(event) =>
            setCreateForm((current) => ({ ...current, fecha_mantenimiento: event.target.value }))
          }
        />

        <Input
          label="Próximo mantenimiento"
          type="date"
          value={createForm.fecha_proximo_mantenimiento}
          onChange={(event) =>
            setCreateForm((current) => ({ ...current, fecha_proximo_mantenimiento: event.target.value }))
          }
        />

        <Input
          label="Kilometraje"
          type="number"
          value={createForm.kilometraje}
          onChange={(event) =>
            setCreateForm((current) => ({ ...current, kilometraje: event.target.value }))
          }
        />
      </div>

      <Textarea
        label="Descripción"
        value={createForm.descripcion}
        onChange={(event) =>
          setCreateForm((current) => ({ ...current, descripcion: event.target.value }))
        }
      />
      <Textarea
        label="Observaciones"
        value={createForm.observaciones}
        onChange={(event) =>
          setCreateForm((current) => ({ ...current, observaciones: event.target.value }))
        }
      />

      {createError ? (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {createError}
        </div>
      ) : null}

      {createForm.entidad_tipo === "TRAILER" && availableTrailers.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">
          No hay tráilers activos y disponibles para enviar a mantenimiento en este momento.
        </p>
      ) : null}
      {createForm.entidad_tipo === "CAJA" && availableCajas.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">
          No hay cajas activas y disponibles para enviar a mantenimiento en este momento.
        </p>
      ) : null}
    </>
  );

  useEffect(() => {
    if (focusMaintenanceId === null) {
      return;
    }
    const found = filtered.find((mantenimiento) => mantenimiento.id_mantenimiento === focusMaintenanceId);
    if (found) {
      setSelectedMaintenanceId(found.id_mantenimiento);
      setDetailForm(buildDetailForm(found));
    }
  }, [filtered, focusMaintenanceId]);

  useEffect(() => {
    const entidadTipo = searchParams.get("entidad_tipo");
    const entidadId = searchParams.get("entidad_id");
    if (!canCreate || !entidadTipo || !entidadId) {
      return;
    }
    if (entidadTipo !== "TRAILER" && entidadTipo !== "CAJA") {
      return;
    }

    setCreateForm((current) => ({
      ...current,
      entidad_tipo: entidadTipo,
      entidad_id: entidadId,
    }));
    setCreateError(null);
    setCreateModalOpen(true);

    router.replace(listBasePath);
  }, [canCreate, listBasePath, router, searchParams]);

  useEffect(() => {
    if (!canCreate || !startCreate || maintenanceCreateOnly) {
      return;
    }
    setCreateError(null);
    setCreateModalOpen(true);
  }, [canCreate, maintenanceCreateOnly, startCreate]);

  async function handleCreate() {
    setCreating(true);
    setCreateError(null);
    try {
      const payload: CreateMantenimientoPayload = {
        entidad_tipo: createForm.entidad_tipo,
        entidad_id: Number(createForm.entidad_id),
        tipo_mantenimiento: createForm.tipo_mantenimiento,
        fecha_mantenimiento: createForm.fecha_mantenimiento || null,
        fecha_proximo_mantenimiento: createForm.fecha_proximo_mantenimiento || null,
        kilometraje: createForm.kilometraje ? Number(createForm.kilometraje) : null,
        descripcion: createForm.descripcion.trim(),
        observaciones: createForm.observaciones.trim() || null,
      };
      const created = await createMantenimientoRequest(payload);
      setCreateModalOpen(false);
      setCreateForm(initialCreateForm);
      await load();
      setSelectedMaintenanceId(created.id_mantenimiento);
      if (maintenanceMode) {
        router.replace(`/mantenimiento/${created.id_mantenimiento}`);
      }
    } catch (currentError) {
      setCreateError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible crear el mantenimiento"
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleSaveDetail() {
    if (!selectedMaintenance || !detailForm) {
      return;
    }
    setSavingDetail(true);
    setDetailError(null);
    try {
      await updateMantenimientoRequest(selectedMaintenance.id_mantenimiento, {
        fecha_mantenimiento: detailForm.fecha_mantenimiento || null,
        fecha_proximo_mantenimiento: detailForm.fecha_proximo_mantenimiento || null,
        kilometraje: detailForm.kilometraje ? Number(detailForm.kilometraje) : null,
        descripcion: detailForm.descripcion.trim(),
        observaciones: detailForm.observaciones.trim() || null,
      });
      await load();
      if (maintenanceMode) {
        router.replace(`/mantenimiento/${selectedMaintenance.id_mantenimiento}`);
      }
    } catch (currentError) {
      setDetailError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible actualizar el mantenimiento"
      );
    } finally {
      setSavingDetail(false);
    }
  }

  async function handleChecklistSave(itemId: number, completado: boolean) {
    if (!selectedMaintenance) {
      return;
    }
    setChecklistSavingId(itemId);
    setDetailError(null);
    try {
      await updateMantenimientoChecklistItemRequest(selectedMaintenance.id_mantenimiento, itemId, {
        completado,
        observaciones: checklistDrafts[itemId] || null,
      });
      await load();
      if (maintenanceMode) {
        router.replace(listBasePath);
      }
    } catch (currentError) {
      setDetailError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible actualizar el checklist"
      );
    } finally {
      setChecklistSavingId(null);
    }
  }

  async function handleCloseMaintenance() {
    if (!selectedMaintenance) {
      return;
    }
    if (!window.confirm("¿Deseas cerrar este mantenimiento?")) {
      return;
    }
    setActionBusy("cerrar");
    setDetailError(null);
    try {
      await cerrarMantenimientoRequest(selectedMaintenance.id_mantenimiento, {
        observaciones: detailForm?.observaciones.trim() || null,
      });
      await load();
    } catch (currentError) {
      setDetailError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cerrar el mantenimiento"
      );
    } finally {
      setActionBusy(null);
    }
  }

  async function handleCancelMaintenance() {
    if (!selectedMaintenance) {
      return;
    }
    if (!window.confirm("¿Deseas cancelar este mantenimiento?")) {
      return;
    }
    setActionBusy("cancelar");
    setDetailError(null);
    try {
      await cancelarMantenimientoRequest(selectedMaintenance.id_mantenimiento, {
        observaciones: detailForm?.observaciones.trim() || null,
      });
      await load();
    } catch (currentError) {
      setDetailError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cancelar el mantenimiento"
      );
    } finally {
      setActionBusy(null);
    }
  }

  function openCreateArchivoModal() {
    setEditingArchivo(null);
    setArchivoForm(initialArchivoForm);
    setArchivoError(null);
    setArchivoModalOpen(true);
  }

  function openEditArchivoModal(archivo: MantenimientoArchivoRecord) {
    setEditingArchivo(archivo);
    setArchivoForm({
      tipo_archivo: archivo.tipo_archivo,
      comentario: archivo.comentario ?? "",
      file: null,
    });
    setArchivoError(null);
    setArchivoModalOpen(true);
  }

  async function handleArchivoSubmit() {
    if (!selectedMaintenance) {
      setArchivoError("Guarda o selecciona un mantenimiento antes de adjuntar archivos");
      return;
    }

    setArchivoSubmitting(true);
    setArchivoError(null);

    try {
      let idArchivo = editingArchivo?.id_archivo ?? null;

      if (archivoForm.file) {
        const presign = await getPresignedUrlRequest({
          filename: archivoForm.file.name,
          content_type: archivoForm.file.type || "application/octet-stream",
          size_bytes: archivoForm.file.size,
        });
        await uploadFileToR2(presign.upload_url, archivoForm.file);
        idArchivo = presign.id_archivo;
      }

      if (!idArchivo) {
        throw new Error("Selecciona un archivo para continuar");
      }

      if (editingArchivo) {
        await updateMantenimientoArchivoRequest(
          selectedMaintenance.id_mantenimiento,
          editingArchivo.id_mantenimiento_archivo,
          {
            tipo_archivo: archivoForm.tipo_archivo,
            comentario: archivoForm.comentario.trim() || null,
          }
        );
      } else {
        await createMantenimientoArchivoRequest(selectedMaintenance.id_mantenimiento, {
          id_archivo: idArchivo,
          tipo_archivo: archivoForm.tipo_archivo,
          comentario: archivoForm.comentario.trim() || null,
        });
      }

      setArchivoModalOpen(false);
      setArchivoForm(initialArchivoForm);
      setEditingArchivo(null);
      await load();
    } catch (currentError) {
      setArchivoError(
        currentError instanceof ApiError
          ? currentError.message
          : currentError instanceof Error
            ? currentError.message
            : "No fue posible guardar el archivo del mantenimiento"
      );
    } finally {
      setArchivoSubmitting(false);
    }
  }

  async function handleToggleArchivoActivo(archivo: MantenimientoArchivoRecord) {
    if (!selectedMaintenance) {
      return;
    }
    const confirmed = window.confirm(
      archivo.activo
        ? "¿Deseas desactivar este archivo del mantenimiento?"
        : "¿Deseas reactivar este archivo del mantenimiento?"
    );
    if (!confirmed) {
      return;
    }

    try {
      if (archivo.activo) {
        await deleteMantenimientoArchivoRequest(
          selectedMaintenance.id_mantenimiento,
          archivo.id_mantenimiento_archivo
        );
      } else {
        await updateMantenimientoArchivoRequest(
          selectedMaintenance.id_mantenimiento,
          archivo.id_mantenimiento_archivo,
          { activo: true }
        );
      }
      await load();
    } catch (currentError) {
      setDetailError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible actualizar el archivo del mantenimiento"
      );
    }
  }

  function openCreateChecklistEvidenceModal(itemId: number) {
    setSelectedChecklistItemForEvidence(itemId);
    setEditingChecklistEvidence(null);
    setChecklistEvidenceForm(initialChecklistEvidenceForm);
    setChecklistEvidenceError(null);
    setChecklistEvidenceModalOpen(true);
  }

  function openEditChecklistEvidenceModal(
    itemId: number,
    evidencia: MantenimientoChecklistEvidenciaRecord
  ) {
    setSelectedChecklistItemForEvidence(itemId);
    setEditingChecklistEvidence(evidencia);
    setChecklistEvidenceForm({
      comentario: evidencia.comentario ?? "",
      file: null,
    });
    setChecklistEvidenceError(null);
    setChecklistEvidenceModalOpen(true);
  }

  async function handleChecklistEvidenceFileChange(file: File | null) {
    setChecklistEvidenceError(null);

    if (!file) {
      revokePreparedEvidenceFile(checklistEvidenceForm.file);
      setChecklistEvidenceForm((current) => ({
        ...current,
        file: null,
      }));
      return;
    }

    try {
      const preparedFile = await prepareEvidenceFile(file, { allowPdf: !maintenanceMode });
      revokePreparedEvidenceFile(checklistEvidenceForm.file);
      setChecklistEvidenceForm((current) => ({
        ...current,
        file: preparedFile,
      }));
    } catch (currentError) {
      setChecklistEvidenceError(
        currentError instanceof Error
          ? currentError.message
          : "No fue posible preparar la imagen seleccionada."
      );
    }
  }

  async function handleChecklistEvidenceSubmit() {
    if (!selectedMaintenance || selectedChecklistItemForEvidence === null) {
      setChecklistEvidenceError("Selecciona un rubro del checklist antes de adjuntar evidencias");
      return;
    }

    setChecklistEvidenceSubmitting(true);
    setChecklistEvidenceError(null);
    try {
      if (editingChecklistEvidence) {
        await updateChecklistItemEvidenciaRequest(
          selectedMaintenance.id_mantenimiento,
          selectedChecklistItemForEvidence,
          editingChecklistEvidence.id_checklist_evidencia,
          {
            comentario: checklistEvidenceForm.comentario.trim() || null,
          }
        );
        } else {
          if (!checklistEvidenceForm.file) {
            throw new Error("Selecciona una foto o archivo para continuar");
          }
          const presign = await getPresignedUrlRequest({
            filename: checklistEvidenceForm.file.file.name,
            content_type: checklistEvidenceForm.file.file.type || "application/octet-stream",
            size_bytes: checklistEvidenceForm.file.file.size,
          });
        await uploadFileToR2(presign.upload_url, checklistEvidenceForm.file.file);
          await createChecklistItemEvidenciaRequest(
            selectedMaintenance.id_mantenimiento,
            selectedChecklistItemForEvidence,
            {
            id_archivo: presign.id_archivo,
            comentario: checklistEvidenceForm.comentario.trim() || null,
          }
        );
      }

        setChecklistEvidenceModalOpen(false);
        setEditingChecklistEvidence(null);
        setSelectedChecklistItemForEvidence(null);
        revokePreparedEvidenceFile(checklistEvidenceForm.file);
        setChecklistEvidenceForm(initialChecklistEvidenceForm);
        await load();
    } catch (currentError) {
      setChecklistEvidenceError(
        currentError instanceof ApiError
          ? currentError.message
          : currentError instanceof Error
            ? currentError.message
            : "No fue posible guardar la evidencia del rubro"
      );
    } finally {
      setChecklistEvidenceSubmitting(false);
    }
  }

  async function handleToggleChecklistEvidenceActivo(
    itemId: number,
    evidencia: MantenimientoChecklistEvidenciaRecord
  ) {
    if (!selectedMaintenance) {
      return;
    }
    const confirmed = window.confirm(
      evidencia.activo
        ? "¿Deseas desactivar esta evidencia del rubro?"
        : "¿Deseas reactivar esta evidencia del rubro?"
    );
    if (!confirmed) {
      return;
    }

    try {
      if (evidencia.activo) {
        await deleteChecklistItemEvidenciaRequest(
          selectedMaintenance.id_mantenimiento,
          itemId,
          evidencia.id_checklist_evidencia
        );
      } else {
        await updateChecklistItemEvidenciaRequest(
          selectedMaintenance.id_mantenimiento,
          itemId,
          evidencia.id_checklist_evidencia,
          { activo: true }
        );
      }
      await load();
    } catch (currentError) {
      setDetailError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible actualizar la evidencia del rubro"
      );
    }
  }

  if (loading) {
    return <LoadingState label="Cargando mantenimientos..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  if (maintenanceCreateOnly) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-300">Taller</p>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold text-white">Nueva orden</h1>
              <p className="text-sm text-slate-300">
                Registra la entrada del recurso al taller y genera su checklist base.
              </p>
            </div>
            <Button type="button" variant="secondary" onClick={() => router.replace(listBasePath)}>
              Volver
            </Button>
          </div>
        </div>

        <Card className="border-white/10 bg-white p-5 shadow-soft">
          <div className="space-y-5">
            {createFormContent}
            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                onClick={() => void handleCreate()}
                disabled={creating || !createForm.entidad_id || !createForm.descripcion.trim()}
              >
                {creating ? "Creando..." : "Crear orden"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => router.replace(listBasePath)}>
                Cancelar
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (maintenanceListOnly) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-300">Taller</p>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold text-white">Órdenes de mantenimiento</h1>
              <p className="text-sm text-slate-300">Consulta tus órdenes activas y abre el detalle para trabajar rubro por rubro.</p>
            </div>
            <Button type="button" onClick={() => router.replace("/mantenimiento/nuevo")}>
              Nueva orden
            </Button>
          </div>
        </div>

        <Card className="border-white/10 bg-white/95 p-4 shadow-soft">
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              label="Buscar"
              placeholder="Recurso, descripción o estatus"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Estatus</span>
              <select
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as MantenimientoFilter)}
              >
                {statusOptions.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </Card>

        {filtered.length === 0 ? (
          <Card className="border-white/10 bg-white p-6 shadow-soft">
            <AdminEmptyState
              title="No tienes órdenes de mantenimiento abiertas"
              description="Cuando entre un tráiler o una caja al taller, podrás registrar aquí la nueva orden."
            />
            <div className="mt-4 flex justify-center">
              <Button type="button" onClick={() => router.replace("/mantenimiento/nuevo")}>
                Crear nueva orden
              </Button>
            </div>
          </Card>
        ) : (
          <div className="space-y-3">
            {filtered.map((mantenimiento) => {
              const completedItems = mantenimiento.checklist_items.filter((item) => item.completado).length;
              return (
                <Card key={mantenimiento.id_mantenimiento} className="border-white/10 bg-white p-4 shadow-soft">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">
                          {mantenimiento.entidad_tipo}
                        </p>
                        <h3 className="mt-1 font-semibold text-slate-950">{mantenimiento.entidad.etiqueta}</h3>
                        <p className="text-sm text-slate-500">{mantenimiento.entidad.subtitulo ?? "Sin subtítulo"}</p>
                      </div>
                      <span
                        className={cn(
                          "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                          getStatusBadgeClass(mantenimiento.estatus)
                        )}
                      >
                        {mantenimiento.estatus}
                      </span>
                    </div>
                    <div className="grid gap-2 text-sm text-slate-600">
                      <div>Tipo: {mantenimiento.tipo_mantenimiento}</div>
                      <div>Fecha mantenimiento: {mantenimiento.fecha_mantenimiento ?? "Sin fecha capturada"}</div>
                      <div>Próxima fecha: {mantenimiento.fecha_proximo_mantenimiento ?? "Sin programar"}</div>
                      <div>Progreso checklist: {completedItems}/{mantenimiento.checklist_items.length}</div>
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => router.replace(`/mantenimiento/${mantenimiento.id_mantenimiento}`)}
                    >
                      Abrir
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  if (detailOnlyView && (!selectedMaintenance || !detailForm)) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <p
            className={cn(
              "text-xs font-semibold uppercase tracking-[0.2em]",
              maintenanceMode ? "text-brand-300" : "text-brand-700"
            )}
          >
            {maintenanceMode ? "Taller" : "Administración"}
          </p>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className={cn("text-2xl font-semibold", maintenanceMode ? "text-white" : "text-slate-950")}>
                Detalle de la orden
              </h1>
              <p className={cn("text-sm", maintenanceMode ? "text-slate-300" : "text-slate-600")}>
                {maintenanceMode
                  ? "Documenta el checklist, sube evidencias por rubro y cierra la orden cuando quede lista."
                  : "No fue posible cargar la orden seleccionada para auditoría administrativa."}
              </p>
            </div>
            <Button type="button" variant="secondary" onClick={() => router.replace(listBasePath)}>
              Volver
            </Button>
          </div>
        </div>
        <Card className="border-white/10 bg-white p-6 shadow-soft">
          <AdminEmptyState
            title="Orden no encontrada"
            description="No fue posible cargar la orden seleccionada o ya no está disponible para este usuario."
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {detailOnlyView ? (
        <div className="space-y-2">
          <p
            className={cn(
              "text-xs font-semibold uppercase tracking-[0.2em]",
              maintenanceMode ? "text-brand-300" : "text-brand-700"
            )}
          >
            {maintenanceMode ? "Taller" : "Administración"}
          </p>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className={cn("text-2xl font-semibold", maintenanceMode ? "text-white" : "text-slate-950")}>
                Detalle de la orden
              </h1>
              <p className={cn("text-sm", maintenanceMode ? "text-slate-300" : "text-slate-600")}>
                {maintenanceMode
                  ? "Aquí puedes revisar la información, completar checklist y documentar archivos del mantenimiento."
                  : "Consulta checklist, evidencias por rubro, archivos generales y acciones administrativas disponibles."}
              </p>
            </div>
            <Button type="button" variant="secondary" onClick={() => router.replace(listBasePath)}>
              Volver
            </Button>
          </div>
        </div>
      ) : (
        <AdminPageHeader
          eyebrow={maintenanceMode ? "Taller" : "Administración"}
          title={maintenanceMode ? "Órdenes de mantenimiento" : "Mantenimientos"}
          description={
            maintenanceMode
              ? "Levanta órdenes de taller, documenta el checklist y deja listo el recurso para volver a operación."
              : "Consola de consulta y auditoría de mantenimientos sobre tráilers y cajas."
          }
        />
      )}

      {showListPanel ? (
      <Card className="border-brand-100 p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="grid gap-3 md:grid-cols-3">
            <Input
              label="Buscar"
              placeholder="Recurso, descripción o estatus"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Estatus</span>
              <select
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as MantenimientoFilter)}
              >
                {statusOptions.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Entidad</span>
              <select
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                value={entityFilter}
                onChange={(event) => setEntityFilter(event.target.value as EntityFilter)}
              >
                {entityOptions.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {canCreate ? (
            <Button type="button" variant="primary" onClick={() => setCreateModalOpen(true)}>
              Nueva orden
            </Button>
          ) : null}
        </div>
      </Card>
      ) : null}

      <div className={cn("grid gap-6", showListPanel && showDetailPanel ? "xl:grid-cols-[1.15fr_0.85fr]" : "")}>
        {showListPanel ? (
        <AdminTableShell
          title={`${maintenanceMode ? "Mis órdenes" : "Listado de mantenimientos"} (${filtered.length})`}
        >
          {filtered.length === 0 ? (
            <AdminEmptyState
              title="No hay mantenimientos para mostrar"
              description={
                maintenanceMode
                  ? "Crea una nueva orden o ajusta los filtros para continuar."
                  : "No hay órdenes que coincidan con los filtros actuales."
              }
            />
          ) : (
            maintenanceMode ? (
              <div className="space-y-3">
                {filtered.map((mantenimiento) => {
                  const completedItems = mantenimiento.checklist_items.filter((item) => item.completado).length;
                  return (
                    <Card
                      key={mantenimiento.id_mantenimiento}
                      className={cn(
                        "border-slate-200 p-4",
                        selectedMaintenanceId === mantenimiento.id_mantenimiento && "border-brand-300 bg-brand-50/30"
                      )}
                    >
                      <div className="space-y-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">
                              {mantenimiento.entidad_tipo}
                            </p>
                            <h3 className="mt-1 font-semibold text-slate-950">
                              {mantenimiento.entidad.etiqueta}
                            </h3>
                            <p className="text-sm text-slate-500">
                              {mantenimiento.entidad.subtitulo ?? "Sin subtítulo"}
                            </p>
                          </div>
                          <span
                            className={cn(
                              "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                              getStatusBadgeClass(mantenimiento.estatus)
                            )}
                          >
                            {mantenimiento.estatus}
                          </span>
                        </div>
                        <div className="grid gap-2 text-sm text-slate-600">
                          <div>Tipo: {mantenimiento.tipo_mantenimiento}</div>
                          <div>Fecha: {mantenimiento.fecha_mantenimiento ?? "Sin fecha capturada"}</div>
                          <div>
                            Progreso checklist: {completedItems}/{mantenimiento.checklist_items.length}
                          </div>
                          <div>{mantenimiento.descripcion}</div>
                        </div>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => {
                            setSelectedMaintenanceId(mantenimiento.id_mantenimiento);
                            router.push(`${detailBasePath}/${mantenimiento.id_mantenimiento}`);
                          }}
                        >
                          Ver detalle
                        </Button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            ) : (
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    {["Entidad", "Tipo", "Estatus", "Inicio", "Descripción", "Acción"].map((header) => (
                      <th
                        key={header}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((mantenimiento) => (
                    <tr
                      key={mantenimiento.id_mantenimiento}
                      className={cn(
                        "border-t border-slate-100",
                        selectedMaintenanceId === mantenimiento.id_mantenimiento && "bg-brand-50/40"
                      )}
                    >
                      <td className="px-4 py-4 text-slate-700">
                        <div className="font-semibold text-slate-950">{mantenimiento.entidad.etiqueta}</div>
                        <div className="text-xs text-slate-500">
                          {mantenimiento.entidad_tipo} · {mantenimiento.entidad.subtitulo ?? "Sin subtítulo"}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-slate-700">{mantenimiento.tipo_mantenimiento}</td>
                      <td className="px-4 py-4">
                        <span
                          className={cn(
                            "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                            getStatusBadgeClass(mantenimiento.estatus)
                          )}
                        >
                          {mantenimiento.estatus}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        {new Date(mantenimiento.fecha_inicio).toLocaleString("es-MX")}
                      </td>
                      <td className="px-4 py-4 text-slate-700">{mantenimiento.descripcion}</td>
                      <td className="px-4 py-4">
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => router.push(`${detailBasePath}/${mantenimiento.id_mantenimiento}`)}
                        >
                          Ver detalle
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
        </AdminTableShell>
        ) : null}

        {showDetailPanel ? (
        <Card className="border-brand-100 p-5">
          {!selectedMaintenance || !detailForm ? (
            <AdminEmptyState
              title="Selecciona un mantenimiento"
              description={
                maintenanceMode
                  ? "Aquí podrás documentar el checklist, adjuntar evidencias por rubro y cerrar la orden."
                  : "Aquí podrás revisar el checklist, archivos y evidencias del mantenimiento."
              }
            />
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">
                    {selectedMaintenance.entidad_tipo}
                  </p>
                  <h3 className="mt-2 text-2xl font-semibold text-slate-950">
                    {selectedMaintenance.entidad.etiqueta}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {selectedMaintenance.entidad.subtitulo ?? "Sin subtítulo"}
                  </p>
                </div>
                <span
                  className={cn(
                    "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                    getStatusBadgeClass(selectedMaintenance.estatus)
                  )}
                >
                  {selectedMaintenance.estatus}
                </span>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Tipo de mantenimiento</span>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
                    {detailForm.tipo_mantenimiento}
                  </div>
                </label>
                <div className="space-y-2">
                  <span className="text-sm font-medium text-slate-700">Estatus</span>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
                    {selectedMaintenance.estatus}
                  </div>
                </div>
                <Input
                  label="Kilometraje"
                  type="number"
                  value={detailForm.kilometraje}
                  readOnly={!canOperate}
                  onChange={(event) =>
                    setDetailForm((current) =>
                      current ? { ...current, kilometraje: event.target.value } : current
                    )
                  }
                />
                <Input label="Inicio" value={new Date(selectedMaintenance.fecha_inicio).toLocaleString("es-MX")} readOnly />
                <Input
                  label="Fecha del mantenimiento"
                  type="date"
                  value={detailForm.fecha_mantenimiento}
                  readOnly={!canOperate}
                  onChange={(event) =>
                    setDetailForm((current) =>
                      current ? { ...current, fecha_mantenimiento: event.target.value } : current
                    )
                  }
                />
                <Input
                  label="Próximo mantenimiento"
                  type="date"
                  value={detailForm.fecha_proximo_mantenimiento}
                  readOnly={!canOperate}
                  onChange={(event) =>
                    setDetailForm((current) =>
                      current ? { ...current, fecha_proximo_mantenimiento: event.target.value } : current
                    )
                  }
                />
              </div>

              <Textarea
                label="Descripción"
                value={detailForm.descripcion}
                readOnly={!canOperate}
                onChange={(event) =>
                  setDetailForm((current) =>
                    current ? { ...current, descripcion: event.target.value } : current
                  )
                }
              />
              <Textarea
                label="Observaciones"
                value={detailForm.observaciones}
                readOnly={!canOperate}
                onChange={(event) =>
                  setDetailForm((current) =>
                    current ? { ...current, observaciones: event.target.value } : current
                  )
                }
              />

              {canOperate || canCloseMaintenance ? (
                <div className="flex flex-wrap gap-3">
                  {canOperate ? (
                    <Button type="button" onClick={() => void handleSaveDetail()} disabled={savingDetail}>
                      {savingDetail ? "Guardando..." : "Guardar mantenimiento"}
                    </Button>
                  ) : null}
                  {canCloseMaintenance ? (
                    <Button
                      type="button"
                      variant="success"
                      onClick={() => void handleCloseMaintenance()}
                      disabled={actionBusy !== null}
                    >
                      {actionBusy === "cerrar" ? "Cerrando..." : "Cerrar orden"}
                    </Button>
                  ) : null}
                  {canCancelMaintenance ? (
                    <Button
                      type="button"
                      variant="danger"
                      onClick={() => void handleCancelMaintenance()}
                      disabled={actionBusy !== null}
                    >
                      {actionBusy === "cancelar" ? "Cancelando..." : "Cancelar orden"}
                    </Button>
                  ) : null}
                </div>
              ) : null}

              {checklistWarning ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Hay {checklistWarning.incomplete} rubros pendientes y {checklistWarning.withoutEvidence} rubros
                  sin evidencia. Puedes cerrar el mantenimiento, pero conviene documentarlos antes.
                </div>
              ) : null}

              {detailError ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {detailError}
                </div>
              ) : null}

              <div className="space-y-4">
                <div>
                  <h4 className="text-lg font-semibold text-slate-950">Checklist</h4>
                  <p className="text-sm text-slate-500">
                    Marca cada revisión completada y agrega observaciones cuando aplique.
                  </p>
                </div>

                {selectedMaintenance.checklist_items.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                    Este mantenimiento aún no tiene checklist base.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {selectedMaintenance.checklist_items.map((item) => (
                      <details
                        key={item.id_item}
                        className={cn(
                          "rounded-2xl border border-slate-200 bg-white",
                          detailOnlyView ? "shadow-soft" : ""
                        )}
                        open={!detailOnlyView}
                      >
                        <summary className="flex cursor-pointer list-none items-start justify-between gap-3 p-4">
                          <div>
                            <p className="font-semibold text-slate-950">{item.nombre}</p>
                            {item.descripcion ? (
                              <p className="text-sm text-slate-500">{item.descripcion}</p>
                            ) : null}
                          </div>
                          <span
                            className={cn(
                              "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                              item.completado
                                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                : "border-amber-200 bg-amber-50 text-amber-700"
                            )}
                          >
                            {item.completado ? "Completado" : "Pendiente"}
                          </span>
                        </summary>
                        <div className="px-4 pb-4">
                        <div className="flex flex-col gap-3">
                          {!detailOnlyView ? (
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-semibold text-slate-950">{item.nombre}</p>
                              {item.descripcion ? (
                                <p className="text-sm text-slate-500">{item.descripcion}</p>
                              ) : null}
                            </div>
                            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                              <input
                                checked={item.completado}
                                disabled={!canOperate}
                                onChange={(event) =>
                                  void handleChecklistSave(item.id_item, event.target.checked)
                                }
                                type="checkbox"
                              />
                              Completado
                            </label>
                          </div>
                          ) : (
                            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                              <input
                                checked={item.completado}
                                disabled={!canOperate}
                                onChange={(event) =>
                                  void handleChecklistSave(item.id_item, event.target.checked)
                                }
                                type="checkbox"
                              />
                              Marcar rubro como completado
                            </label>
                          )}
                          <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                            <div className="text-sm text-slate-600">
                              {item.evidencias.filter((evidencia) => evidencia.activo).length} evidencias
                            </div>
                            {canOperate ? (
                              <Button
                                type="button"
                                variant="secondary"
                                onClick={() => openCreateChecklistEvidenceModal(item.id_item)}
                              >
                                Agregar evidencia
                              </Button>
                            ) : null}
                          </div>
                          <Textarea
                            label="Observaciones del item"
                            value={checklistDrafts[item.id_item] ?? ""}
                            readOnly={!canOperate}
                            onChange={(event) =>
                              setChecklistDrafts((current) => ({
                                ...current,
                                [item.id_item]: event.target.value,
                              }))
                            }
                          />
                          {canOperate ? (
                            <div className="flex justify-end">
                              <Button
                                type="button"
                                variant="secondary"
                                onClick={() => void handleChecklistSave(item.id_item, item.completado)}
                                disabled={checklistSavingId === item.id_item}
                              >
                                {checklistSavingId === item.id_item ? "Guardando..." : "Guardar item"}
                              </Button>
                            </div>
                          ) : null}
                          {item.evidencias.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-500">
                              Sin evidencias del rubro
                            </div>
                          ) : (
                            <div className="grid gap-3 md:grid-cols-2">
                              {item.evidencias.map((evidencia) => {
                                const url = evidencia.archivo?.url_publica ?? null;
                                const contentType = evidencia.archivo?.content_type ?? null;
                                return (
                                  <Card key={evidencia.id_checklist_evidencia} className="border-slate-200 p-3">
                                    <div className="space-y-3">
                                      <div className="flex items-start justify-between gap-2">
                                        <div>
                                          <p className="text-sm font-semibold text-slate-950">
                                            {evidencia.archivo?.nombre_original ?? "Archivo sin nombre"}
                                          </p>
                                          <p className="text-xs text-slate-500">
                                            {evidencia.comentario ?? "Sin comentario"}
                                          </p>
                                        </div>
                                        <span
                                          className={cn(
                                            "inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold",
                                            evidencia.activo
                                              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                              : "border-slate-200 bg-slate-100 text-slate-600"
                                          )}
                                        >
                                          {evidencia.activo ? "Activa" : "Inactiva"}
                                        </span>
                                      </div>

                                      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                                        {url && isImageFile(contentType) ? (
                                          <img
                                            src={url}
                                            alt={evidencia.archivo?.nombre_original ?? "Evidencia del rubro"}
                                            className="h-32 w-full object-cover"
                                          />
                                        ) : (
                                          <div className="flex h-32 items-center justify-center px-4 text-center text-sm text-slate-500">
                                            {isPdfFile(contentType)
                                              ? "PDF listo para ver o descargar"
                                              : "Vista previa no disponible para este archivo"}
                                          </div>
                                        )}
                                      </div>

                                      <div className="flex flex-wrap gap-2">
                                        {url ? (
                                          <>
                                            <a href={url} rel="noopener noreferrer" target="_blank">
                                              <Button type="button" variant="secondary">
                                                Ver
                                              </Button>
                                            </a>
                                            <a
                                              href={url}
                                              rel="noopener noreferrer"
                                              target="_blank"
                                              download={
                                                evidencia.archivo?.nombre_original ??
                                                `checklist-${evidencia.id_checklist_evidencia}`
                                              }
                                            >
                                              <Button type="button" variant="ghost">
                                                Descargar
                                              </Button>
                                            </a>
                                          </>
                                        ) : (
                                          <span className="rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slate-500">
                                            Sin URL disponible
                                          </span>
                                        )}
                                        {canOperate ? (
                                          <>
                                            <Button
                                              type="button"
                                              variant="ghost"
                                              onClick={() =>
                                                openEditChecklistEvidenceModal(item.id_item, evidencia)
                                              }
                                            >
                                              Editar
                                            </Button>
                                  <Button
                                    type="button"
                                    variant={evidencia.activo ? "warning" : "success"}
                                    onClick={() =>
                                      void handleToggleChecklistEvidenceActivo(item.id_item, evidencia)
                                    }
                                            >
                                              {evidencia.activo ? "Desactivar" : "Reactivar"}
                                            </Button>
                                          </>
                                        ) : null}
                                      </div>
                                    </div>
                                  </Card>
                                );
                              })}
                            </div>
                          )}
                        </div>
                        </div>
                      </details>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-lg font-semibold text-slate-950">Archivos del mantenimiento</h4>
                    <p className="text-sm text-slate-500">
                      Adjunta fotos, facturas, diagnósticos y comprobantes relacionados con este servicio.
                    </p>
                  </div>
                  {canOperate ? (
                    <Button type="button" variant="secondary" onClick={openCreateArchivoModal}>
                      Agregar archivo
                    </Button>
                  ) : null}
                </div>

                {selectedMaintenance.archivos.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                    Aún no hay archivos cargados para este mantenimiento.
                  </div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {selectedMaintenance.archivos.map((archivo) => {
                      const contentType = archivo.archivo?.content_type ?? null;
                      const url = archivo.archivo?.url_publica ?? null;
                      return (
                        <Card key={archivo.id_mantenimiento_archivo} className="border-slate-200 p-4">
                          <div className="space-y-3">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="font-semibold text-slate-950">{archivo.tipo_archivo}</p>
                                <p className="text-xs text-slate-500">
                                  {archivo.archivo?.nombre_original ?? "Archivo sin nombre"}
                                </p>
                              </div>
                              <span
                                className={cn(
                                  "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                                  archivo.activo
                                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                    : "border-slate-200 bg-slate-100 text-slate-600"
                                )}
                              >
                                {archivo.activo ? "Activo" : "Inactivo"}
                              </span>
                            </div>

                            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                              {url && isImageFile(contentType) ? (
                                <img
                                  src={url}
                                  alt={archivo.archivo?.nombre_original ?? "Archivo de mantenimiento"}
                                  className="h-40 w-full object-cover"
                                />
                              ) : (
                                <div className="flex h-40 items-center justify-center px-4 text-center text-sm text-slate-500">
                                  {isPdfFile(contentType)
                                    ? "PDF listo para ver o descargar"
                                    : "Vista previa no disponible para este archivo"}
                                </div>
                              )}
                            </div>

                            <div className="text-sm text-slate-600">
                              <div>MIME: {contentType ?? "Sin dato"}</div>
                              <div>Comentario: {archivo.comentario ?? "Sin comentario"}</div>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              {url ? (
                                <>
                                  <a href={url} rel="noopener noreferrer" target="_blank">
                                    <Button type="button" variant="secondary">
                                      Ver
                                    </Button>
                                  </a>
                                  <a
                                    href={url}
                                    rel="noopener noreferrer"
                                    target="_blank"
                                    download={
                                      archivo.archivo?.nombre_original ??
                                      `mantenimiento-${archivo.id_mantenimiento_archivo}`
                                    }
                                  >
                                    <Button type="button" variant="ghost">
                                      Descargar
                                    </Button>
                                  </a>
                                </>
                              ) : (
                                <span className="rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slate-500">
                                  Sin URL disponible
                                </span>
                              )}
                              {canOperate ? (
                                <>
                                  <Button type="button" variant="ghost" onClick={() => openEditArchivoModal(archivo)}>
                                    Editar
                                  </Button>
                                  <Button
                                    type="button"
                                    variant={archivo.activo ? "warning" : "success"}
                                    onClick={() => void handleToggleArchivoActivo(archivo)}
                                  >
                                    {archivo.activo ? "Desactivar" : "Reactivar"}
                                  </Button>
                                </>
                              ) : null}
                            </div>
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </Card>
        ) : null}
      </div>

      <AdminModal
        open={canCreate && createModalOpen}
        title="Nueva orden de mantenimiento"
        description="Registra la entrada del recurso al taller y genera el checklist base para su intervención."
        onClose={() => {
          if (creating) return;
          setCreateModalOpen(false);
          setCreateError(null);
          if (maintenanceMode && startCreate) {
            router.replace(listBasePath);
          }
        }}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Entidad</span>
            <select
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              value={createForm.entidad_tipo}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  entidad_tipo: event.target.value as MantenimientoEntidadTipo,
                  entidad_id: "",
                }))
              }
            >
              <option value="TRAILER">Tráiler</option>
              <option value="CAJA">Caja</option>
            </select>
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Recurso</span>
            <select
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              value={createForm.entidad_id}
              onChange={(event) =>
                setCreateForm((current) => ({ ...current, entidad_id: event.target.value }))
              }
            >
              <option value="">Selecciona un recurso</option>
              {createForm.entidad_tipo === "TRAILER"
                ? availableTrailers.map((item) => (
                    <option key={item.id_trailer} value={item.id_trailer}>
                      {item.numero_economico} · {item.placas}
                    </option>
                  ))
                : availableCajas.map((item) => (
                    <option key={item.id_caja} value={item.id_caja}>
                      {item.numero_economico ?? item.placas} · {item.placas}
                    </option>
                  ))}
            </select>
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Tipo de mantenimiento</span>
            <select
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              value={createForm.tipo_mantenimiento}
              onChange={(event) =>
                setCreateForm((current) => ({
                  ...current,
                  tipo_mantenimiento: event.target.value as MantenimientoTipo,
                }))
              }
            >
              {maintenanceTypeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <Input
            label="Fecha del mantenimiento"
            type="date"
            value={createForm.fecha_mantenimiento}
            onChange={(event) =>
              setCreateForm((current) => ({ ...current, fecha_mantenimiento: event.target.value }))
            }
          />

          <Input
            label="Próximo mantenimiento"
            type="date"
            value={createForm.fecha_proximo_mantenimiento}
            onChange={(event) =>
              setCreateForm((current) => ({ ...current, fecha_proximo_mantenimiento: event.target.value }))
            }
          />

          <Input
            label="Kilometraje"
            type="number"
            value={createForm.kilometraje}
            onChange={(event) =>
              setCreateForm((current) => ({ ...current, kilometraje: event.target.value }))
            }
          />
        </div>

        <Textarea
          label="Descripción"
          value={createForm.descripcion}
          onChange={(event) =>
            setCreateForm((current) => ({ ...current, descripcion: event.target.value }))
          }
        />
        <Textarea
          label="Observaciones"
          value={createForm.observaciones}
          onChange={(event) =>
            setCreateForm((current) => ({ ...current, observaciones: event.target.value }))
          }
        />

        {createError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {createError}
          </div>
        ) : null}

        {createForm.entidad_tipo === "TRAILER" && availableTrailers.length === 0 ? (
          <p className="mt-4 text-sm text-slate-500">
            No hay tráilers activos y disponibles para enviar a mantenimiento en este momento.
          </p>
        ) : null}
        {createForm.entidad_tipo === "CAJA" && availableCajas.length === 0 ? (
          <p className="mt-4 text-sm text-slate-500">
            No hay cajas activas y disponibles para enviar a mantenimiento en este momento.
          </p>
        ) : null}

        <div className="mt-6 flex gap-3">
          <Button
            type="button"
            onClick={() => void handleCreate()}
            disabled={creating || !createForm.entidad_id || !createForm.descripcion.trim()}
          >
            {creating ? "Creando..." : "Crear orden"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setCreateModalOpen(false);
              if (maintenanceMode && startCreate) {
                router.replace(listBasePath);
              }
            }}
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      {!maintenanceMode ? (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-brand-100 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Abiertos</p>
          <p className="mt-3 text-3xl font-semibold text-slate-950">
            {mantenimientos.filter((item) => item.estatus === "ABIERTO").length}
          </p>
        </Card>
        <Card className="border-brand-100 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">En proceso</p>
          <p className="mt-3 text-3xl font-semibold text-slate-950">
            {mantenimientos.filter((item) => item.estatus === "EN_PROCESO").length}
          </p>
        </Card>
        <Card className="border-brand-100 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Cerrados</p>
          <p className="mt-3 text-3xl font-semibold text-slate-950">
            {mantenimientos.filter((item) => item.estatus === "CERRADO").length}
          </p>
        </Card>
        <Card className="border-brand-100 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Cancelados</p>
          <p className="mt-3 text-3xl font-semibold text-slate-950">
            {mantenimientos.filter((item) => item.estatus === "CANCELADO").length}
          </p>
        </Card>
      </div>
      ) : null}

      {!maintenanceMode ? (
      <Card className="border-dashed border-slate-200 p-4 text-sm text-slate-600">
        Mientras el mantenimiento esté en estado <strong>ABIERTO</strong> o <strong>EN_PROCESO</strong>, el
        tráiler o la caja quedarán fuera de disponibilidad y no podrán asignarse a viajes.
      </Card>
      ) : null}

      <AdminModal
        open={archivoModalOpen}
        title={editingArchivo ? "Editar archivo del mantenimiento" : "Agregar archivo al mantenimiento"}
        description={
          editingArchivo
            ? "Actualiza el tipo o comentario del archivo asociado."
            : "Sube evidencia visual o documental para este mantenimiento usando el almacenamiento R2 existente."
        }
        onClose={() => {
          if (archivoSubmitting) return;
          setArchivoModalOpen(false);
          setArchivoError(null);
          setEditingArchivo(null);
          setArchivoForm(initialArchivoForm);
        }}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Tipo de archivo</span>
            <select
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              value={archivoForm.tipo_archivo}
              onChange={(event) =>
                setArchivoForm((current) => ({
                  ...current,
                  tipo_archivo: event.target.value as MantenimientoArchivoTipo,
                }))
              }
            >
              {maintenanceFileTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Archivo</span>
            <input
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              type="file"
              disabled={Boolean(editingArchivo)}
              onChange={(event) =>
                setArchivoForm((current) => ({
                  ...current,
                  file: event.target.files?.[0] ?? null,
                }))
              }
            />
            {editingArchivo ? (
              <p className="text-xs text-slate-500">
                El reemplazo físico del archivo no está habilitado; aquí puedes editar tipo y comentario.
              </p>
            ) : null}
          </label>
        </div>

        <Textarea
          label="Comentario"
          value={archivoForm.comentario}
          onChange={(event) =>
            setArchivoForm((current) => ({ ...current, comentario: event.target.value }))
          }
        />

        {archivoError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {archivoError}
          </div>
        ) : null}

        <div className="mt-6 flex gap-3">
          <Button
            type="button"
            onClick={() => void handleArchivoSubmit()}
            disabled={archivoSubmitting || (!editingArchivo && !archivoForm.file)}
          >
            {archivoSubmitting
              ? editingArchivo
                ? "Guardando..."
                : "Subiendo..."
              : editingArchivo
                ? "Guardar cambios"
                : "Guardar archivo"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setArchivoModalOpen(false);
              setArchivoError(null);
              setEditingArchivo(null);
              setArchivoForm(initialArchivoForm);
            }}
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        open={checklistEvidenceModalOpen}
        title={
          editingChecklistEvidence ? "Editar evidencia del rubro" : "Agregar evidencia al rubro"
        }
        description={
          editingChecklistEvidence
            ? "Actualiza el comentario o reactiva/desactiva la evidencia del rubro."
            : "Sube una o más fotos o archivos asociados específicamente a este rubro del checklist."
        }
        onClose={() => {
          if (checklistEvidenceSubmitting) return;
          setChecklistEvidenceModalOpen(false);
          setSelectedChecklistItemForEvidence(null);
          setEditingChecklistEvidence(null);
          revokePreparedEvidenceFile(checklistEvidenceForm.file);
          setChecklistEvidenceForm(initialChecklistEvidenceForm);
          setChecklistEvidenceError(null);
        }}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Rubro"
            value={
              selectedMaintenance?.checklist_items.find(
                (item) => item.id_item === selectedChecklistItemForEvidence
              )?.nombre ?? "Sin rubro"
            }
            readOnly
          />
          <div className="block space-y-2">
            {editingChecklistEvidence ? (
              <p className="text-xs text-slate-500">
                El reemplazo físico del archivo no está habilitado; aquí puedes editar el comentario.
              </p>
            ) : (
              <EvidenceFilePicker
                disabled={false}
                helperText={
                  maintenanceMode
                    ? "En móvil se intentará abrir la cámara trasera para registrar evidencia del checklist."
                    : "Puedes seleccionar imágenes guardadas o PDFs. No se forzará la cámara."
                }
                label={maintenanceMode ? "Foto de evidencia" : "Archivo de evidencia"}
                mode={maintenanceMode ? "camera" : "file"}
                onFileChange={(file) => void handleChecklistEvidenceFileChange(file)}
                selectedFile={checklistEvidenceForm.file}
              />
            )}
          </div>
        </div>

        <Textarea
          label="Comentario"
          value={checklistEvidenceForm.comentario}
          onChange={(event) =>
            setChecklistEvidenceForm((current) => ({ ...current, comentario: event.target.value }))
          }
        />

        {checklistEvidenceError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {checklistEvidenceError}
          </div>
        ) : null}

        <div className="mt-6 flex gap-3">
          <Button
            type="button"
            onClick={() => void handleChecklistEvidenceSubmit()}
            disabled={checklistEvidenceSubmitting || (!editingChecklistEvidence && !checklistEvidenceForm.file)}
          >
            {checklistEvidenceSubmitting
              ? editingChecklistEvidence
                ? "Guardando..."
                : "Subiendo..."
              : editingChecklistEvidence
                ? "Guardar cambios"
                : "Guardar evidencia"}
          </Button>
          <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setChecklistEvidenceModalOpen(false);
                setSelectedChecklistItemForEvidence(null);
                setEditingChecklistEvidence(null);
                revokePreparedEvidenceFile(checklistEvidenceForm.file);
                setChecklistEvidenceForm(initialChecklistEvidenceForm);
                setChecklistEvidenceError(null);
              }}
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>
    </div>
  );
}

export default function AdminMantenimientosPage() {
  return <MantenimientosWorkbench variant="admin" maintenanceView="list" />;
}
