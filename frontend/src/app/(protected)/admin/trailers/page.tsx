"use client";
import { useCallback, useEffect, useState } from "react";

import { AdminEmptyState } from "@/components/admin/admin-empty-state";
import { AdminModal } from "@/components/admin/admin-modal";
import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AdminTableShell } from "@/components/admin/admin-table-shell";
import { EntityDocumentsSection } from "@/components/admin/entity-documents-section";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError } from "@/services/api-client";
import {
  createTrailerRequest,
  getTrailersRequest,
  updateTrailerRequest
} from "@/services/trailers.service";
import type { CreateTrailerPayload, Trailer, UpdateTrailerPayload } from "@/types/trailer";

type TrailerFormState = {
  numero_economico: string;
  placas: string;
  marca: string;
  modelo: string;
  anio: string;
  poliza_seguro: string;
  seguro_vigencia: string;
  tarjeta_circulacion: string;
  permiso_circulacion: string;
  numero_serie: string;
  verificacion: string;
  verificacion_vigencia: string;
  activo: boolean;
};

const initialForm: TrailerFormState = {
  numero_economico: "",
  placas: "",
  marca: "",
  modelo: "",
  anio: "",
  poliza_seguro: "",
  seguro_vigencia: "",
  tarjeta_circulacion: "",
  permiso_circulacion: "",
  numero_serie: "",
  verificacion: "",
  verificacion_vigencia: "",
  activo: true
};

function toFormState(trailer: Trailer | null): TrailerFormState {
  if (!trailer) {
    return initialForm;
  }

  return {
    numero_economico: trailer.numero_economico,
    placas: trailer.placas,
    marca: trailer.marca ?? "",
    modelo: trailer.modelo ?? "",
    anio: trailer.anio !== null ? String(trailer.anio) : "",
    poliza_seguro: trailer.poliza_seguro ?? "",
    seguro_vigencia: trailer.seguro_vigencia ?? "",
    tarjeta_circulacion: trailer.tarjeta_circulacion ?? "",
    permiso_circulacion: trailer.permiso_circulacion ?? "",
    numero_serie: trailer.numero_serie ?? "",
    verificacion: trailer.verificacion ?? "",
    verificacion_vigencia: trailer.verificacion_vigencia ?? "",
    activo: trailer.activo
  };
}

function buildCreatePayload(form: TrailerFormState): CreateTrailerPayload {
  return {
    numero_economico: form.numero_economico.trim(),
    placas: form.placas.trim(),
    marca: form.marca.trim() || null,
    modelo: form.modelo.trim() || null,
    anio: form.anio ? Number(form.anio) : null,
    poliza_seguro: form.poliza_seguro.trim() || null,
    seguro_vigencia: form.seguro_vigencia || null,
    tarjeta_circulacion: form.tarjeta_circulacion.trim() || null,
    permiso_circulacion: form.permiso_circulacion.trim() || null,
    numero_serie: form.numero_serie.trim() || null,
    verificacion: form.verificacion.trim() || null,
    verificacion_vigencia: form.verificacion_vigencia || null,
    activo: form.activo
  };
}

function buildUpdatePayload(form: TrailerFormState): UpdateTrailerPayload {
  return buildCreatePayload(form);
}

export default function AdminTrailersPage() {
  const [trailers, setTrailers] = useState<Trailer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [form, setForm] = useState<TrailerFormState>(initialForm);
  const [editingTrailer, setEditingTrailer] = useState<Trailer | null>(null);
  const [trailerToToggle, setTrailerToToggle] = useState<Trailer | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const trailersData = await getTrailersRequest();
      setTrailers(trailersData);
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible cargar los tráilers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreateModal() {
    setEditingTrailer(null);
    setForm(initialForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEditModal(trailer: Trailer) {
    setEditingTrailer(trailer);
    setForm(toFormState(trailer));
    setFormError(null);
    setModalOpen(true);
  }

  function openDeleteModal(trailer: Trailer) {
    setTrailerToToggle(trailer);
    setDeleteError(null);
    setDeleteModalOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);

    try {
      if (editingTrailer) {
        await updateTrailerRequest(editingTrailer.id_trailer, buildUpdatePayload(form));
      } else {
        await createTrailerRequest(buildCreatePayload(form));
      }

      setModalOpen(false);
      setEditingTrailer(null);
      setForm(initialForm);
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : editingTrailer
            ? "No fue posible actualizar el tráiler"
            : "No fue posible crear el tráiler"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!trailerToToggle) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      await updateTrailerRequest(trailerToToggle.id_trailer, { activo: !trailerToToggle.activo });
      setDeleteModalOpen(false);
      setTrailerToToggle(null);
      await load();
    } catch (currentError) {
      setDeleteError(
        currentError instanceof ApiError
          ? currentError.message
          : trailerToToggle.activo
            ? "No fue posible desactivar el tráiler"
            : "No fue posible reactivar el tráiler"
      );
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando tráilers..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }
  return (
    <div className="space-y-6">
      <AdminPageHeader
        description="Administra los tractocamiones disponibles para asignación y operación."
        eyebrow="Administración"
        title="Tráilers"
      />

      {trailers.length === 0 ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateModal} type="button">
              Crear tráiler
            </Button>
          </div>
          <AdminEmptyState
            description="Crea el primer tráiler operativo para habilitar asignaciones."
            title="No hay tráilers registrados"
          />
        </div>
      ) : (
        <AdminTableShell
          action={
            <Button onClick={openCreateModal} type="button">
              Crear tráiler
            </Button>
          }
          title="Listado de tráilers"
        >
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["ID", "Número económico", "Placas", "Marca", "Modelo", "Activo", "Acciones"].map((header) => (
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
              {trailers.map((trailer) => (
                <tr key={trailer.id_trailer} className="border-t border-slate-100">
                  <td className="px-4 py-4 text-slate-700">{trailer.id_trailer}</td>
                  <td className="px-4 py-4 font-semibold text-slate-950">{trailer.numero_economico}</td>
                  <td className="px-4 py-4 text-slate-700">{trailer.placas}</td>
                  <td className="px-4 py-4 text-slate-700">{trailer.marca ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">{trailer.modelo ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">
                    <StatusBadge variant={trailer.activo ? "active" : "inactive"}>
                      {trailer.activo ? "Activo" : "Inactivo"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <Button onClick={() => openEditModal(trailer)} type="button" variant="outline">
                        Editar
                      </Button>
                      <Button
                        onClick={() => openDeleteModal(trailer)}
                        type="button"
                        variant={trailer.activo ? "warning" : "success"}
                      >
                        {trailer.activo ? "Desactivar" : "Reactivar"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AdminTableShell>
      )}

      <AdminModal
        description={
          editingTrailer
            ? "Actualiza la información del tráiler seleccionado."
            : "Captura la información base del tráiler."
        }
        onClose={() => {
          if (submitting) return;
          setModalOpen(false);
          setEditingTrailer(null);
          setFormError(null);
        }}
        open={modalOpen}
        title={editingTrailer ? "Editar tráiler" : "Crear tráiler"}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Número económico"
            onChange={(event) => setForm((current) => ({ ...current, numero_economico: event.target.value }))}
            value={form.numero_economico}
          />
          <Input
            label="Placas"
            onChange={(event) => setForm((current) => ({ ...current, placas: event.target.value }))}
            value={form.placas}
          />
          <Input
            label="Marca"
            onChange={(event) => setForm((current) => ({ ...current, marca: event.target.value }))}
            value={form.marca}
          />
          <Input
            label="Modelo"
            onChange={(event) => setForm((current) => ({ ...current, modelo: event.target.value }))}
            value={form.modelo}
          />
          <Input
            label="Año"
            onChange={(event) => setForm((current) => ({ ...current, anio: event.target.value }))}
            type="number"
            value={form.anio}
          />
          <Input
            label="Póliza de seguro"
            onChange={(event) => setForm((current) => ({ ...current, poliza_seguro: event.target.value }))}
            value={form.poliza_seguro}
          />
          <Input
            label="Vigencia seguro"
            onChange={(event) => setForm((current) => ({ ...current, seguro_vigencia: event.target.value }))}
            type="date"
            value={form.seguro_vigencia}
          />
          <Input
            label="Tarjeta de circulación"
            onChange={(event) =>
              setForm((current) => ({ ...current, tarjeta_circulacion: event.target.value }))
            }
            value={form.tarjeta_circulacion}
          />
          <Input
            label="Permiso / número de permiso de circulación"
            onChange={(event) =>
              setForm((current) => ({ ...current, permiso_circulacion: event.target.value }))
            }
            value={form.permiso_circulacion}
          />
          <Input
            label="Número de serie"
            onChange={(event) =>
              setForm((current) => ({ ...current, numero_serie: event.target.value }))
            }
            value={form.numero_serie}
          />
          <Input
            label="Verificación"
            onChange={(event) => setForm((current) => ({ ...current, verificacion: event.target.value }))}
            value={form.verificacion}
          />
          <Input
            label="Vigencia verificación"
            onChange={(event) =>
              setForm((current) => ({ ...current, verificacion_vigencia: event.target.value }))
            }
            type="date"
            value={form.verificacion_vigencia}
          />
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.activo}
              onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))}
              type="checkbox"
            />
            Tráiler activo
          </label>
        </div>
        <EntityDocumentsSection
          entityId={editingTrailer?.id_trailer ?? null}
          entityType="TRAILER"
        />
        {formError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={submitting || !form.numero_economico.trim() || !form.placas.trim()}
            onClick={() => void handleSubmit()}
            type="button"
          >
            {submitting
              ? editingTrailer
                ? "Guardando..."
                : "Creando..."
              : editingTrailer
                ? "Guardar cambios"
                : "Guardar tráiler"}
          </Button>
          <Button
            onClick={() => {
              setModalOpen(false);
              setEditingTrailer(null);
            }}
            type="button"
            variant="ghost"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Este cambio actualizará el estado del tráiler sin borrar su historial."
        onClose={() => {
          if (deleting) return;
          setDeleteModalOpen(false);
          setTrailerToToggle(null);
          setDeleteError(null);
        }}
        open={deleteModalOpen}
        title="Confirmar cambio de estado"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            {trailerToToggle
              ? trailerToToggle.activo
                ? `¿Deseas desactivar el registro ${trailerToToggle.numero_economico}?`
                : `¿Deseas reactivar el registro ${trailerToToggle.numero_economico}?`
              : "¿Deseas actualizar el estado de este tráiler?"}
          </p>
          {deleteError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {deleteError}
            </div>
          ) : null}
          <div className="flex gap-3">
            <Button
              disabled={deleting}
              onClick={() => void handleDelete()}
              type="button"
              variant={trailerToToggle?.activo ? "warning" : "success"}
            >
              {deleting
                ? trailerToToggle?.activo
                  ? "Desactivando..."
                  : "Reactivando..."
                : trailerToToggle?.activo
                  ? "Sí, desactivar"
                  : "Sí, reactivar"}
            </Button>
            <Button
              onClick={() => {
                setDeleteModalOpen(false);
                setTrailerToToggle(null);
                setDeleteError(null);
              }}
              type="button"
              variant="ghost"
            >
              Cancelar
            </Button>
          </div>
        </div>
      </AdminModal>
    </div>
  );
}
