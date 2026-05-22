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
  createCajaRequest,
  getCajasRequest,
  updateCajaRequest
} from "@/services/cajas.service";
import type { Caja, CreateCajaPayload, UpdateCajaPayload } from "@/types/caja";

type CajaFormState = {
  numero_economico: string;
  placas: string;
  tipo_caja: string;
  marca: string;
  modelo: string;
  anio: string;
  tarjeta_circulacion: string;
  numero_serie: string;
  verificacion: string;
  verificacion_vigencia: string;
  activo: boolean;
};

const initialForm: CajaFormState = {
  numero_economico: "",
  placas: "",
  tipo_caja: "",
  marca: "",
  modelo: "",
  anio: "",
  tarjeta_circulacion: "",
  numero_serie: "",
  verificacion: "",
  verificacion_vigencia: "",
  activo: true
};

function toFormState(caja: Caja | null): CajaFormState {
  if (!caja) {
    return initialForm;
  }

  return {
    numero_economico: caja.numero_economico ?? "",
    placas: caja.placas,
    tipo_caja: caja.tipo_caja ?? "",
    marca: caja.marca ?? "",
    modelo: caja.modelo ?? "",
    anio: caja.anio !== null ? String(caja.anio) : "",
    tarjeta_circulacion: caja.tarjeta_circulacion ?? "",
    numero_serie: caja.numero_serie ?? "",
    verificacion: caja.verificacion ?? "",
    verificacion_vigencia: caja.verificacion_vigencia ?? "",
    activo: caja.activo
  };
}

function buildCreatePayload(form: CajaFormState): CreateCajaPayload {
  return {
    numero_economico: form.numero_economico.trim() || null,
    placas: form.placas.trim(),
    tipo_caja: form.tipo_caja.trim() || null,
    marca: form.marca.trim() || null,
    modelo: form.modelo.trim() || null,
    anio: form.anio ? Number(form.anio) : null,
    tarjeta_circulacion: form.tarjeta_circulacion.trim() || null,
    numero_serie: form.numero_serie.trim() || null,
    verificacion: form.verificacion.trim() || null,
    verificacion_vigencia: form.verificacion_vigencia || null,
    activo: form.activo
  };
}

function buildUpdatePayload(form: CajaFormState): UpdateCajaPayload {
  return buildCreatePayload(form);
}

export default function AdminCajasPage() {
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [form, setForm] = useState<CajaFormState>(initialForm);
  const [editingCaja, setEditingCaja] = useState<Caja | null>(null);
  const [cajaToToggle, setCajaToToggle] = useState<Caja | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cajasData = await getCajasRequest();
      setCajas(cajasData);
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible cargar las cajas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreateModal() {
    setEditingCaja(null);
    setForm(initialForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEditModal(caja: Caja) {
    setEditingCaja(caja);
    setForm(toFormState(caja));
    setFormError(null);
    setModalOpen(true);
  }

  function openDeleteModal(caja: Caja) {
    setCajaToToggle(caja);
    setDeleteError(null);
    setDeleteModalOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);

    try {
      if (editingCaja) {
        await updateCajaRequest(editingCaja.id_caja, buildUpdatePayload(form));
      } else {
        await createCajaRequest(buildCreatePayload(form));
      }

      setModalOpen(false);
      setEditingCaja(null);
      setForm(initialForm);
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : editingCaja
            ? "No fue posible actualizar la caja"
            : "No fue posible crear la caja"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!cajaToToggle) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      await updateCajaRequest(cajaToToggle.id_caja, { activo: !cajaToToggle.activo });
      setDeleteModalOpen(false);
      setCajaToToggle(null);
      await load();
    } catch (currentError) {
      setDeleteError(
        currentError instanceof ApiError
          ? currentError.message
          : cajaToToggle.activo
            ? "No fue posible desactivar la caja"
            : "No fue posible reactivar la caja"
      );
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando cajas..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }
  return (
    <div className="space-y-6">
      <AdminPageHeader
        description="Administra las cajas disponibles para asignación dentro del flujo operativo."
        eyebrow="Administración"
        title="Cajas"
      />

      {cajas.length === 0 ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateModal} type="button">
              Crear caja
            </Button>
          </div>
          <AdminEmptyState
            description="Crea la primera caja operativa para habilitar asignaciones completas."
            title="No hay cajas registradas"
          />
        </div>
      ) : (
        <AdminTableShell
          action={
            <Button onClick={openCreateModal} type="button">
              Crear caja
            </Button>
          }
          title="Listado de cajas"
        >
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["ID", "Número económico", "Placas", "Tipo", "Marca", "Activo", "Acciones"].map((header) => (
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
              {cajas.map((caja) => (
                <tr key={caja.id_caja} className="border-t border-slate-100">
                  <td className="px-4 py-4 text-slate-700">{caja.id_caja}</td>
                  <td className="px-4 py-4 font-semibold text-slate-950">{caja.numero_economico ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">{caja.placas}</td>
                  <td className="px-4 py-4 text-slate-700">{caja.tipo_caja ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">{caja.marca ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">
                    <StatusBadge variant={caja.activo ? "active" : "inactive"}>
                      {caja.activo ? "Activo" : "Inactivo"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <Button onClick={() => openEditModal(caja)} type="button" variant="outline">
                        Editar
                      </Button>
                      <Button
                        onClick={() => openDeleteModal(caja)}
                        type="button"
                        variant={caja.activo ? "warning" : "success"}
                      >
                        {caja.activo ? "Desactivar" : "Reactivar"}
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
          editingCaja
            ? "Actualiza la información de la caja seleccionada."
            : "Captura la información base de la caja."
        }
        onClose={() => {
          if (submitting) return;
          setModalOpen(false);
          setEditingCaja(null);
          setFormError(null);
        }}
        open={modalOpen}
        title={editingCaja ? "Editar caja" : "Crear caja"}
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
            label="Tipo de caja"
            onChange={(event) => setForm((current) => ({ ...current, tipo_caja: event.target.value }))}
            value={form.tipo_caja}
          />
          <Input
            label="Marca"
            onChange={(event) => setForm((current) => ({ ...current, marca: event.target.value }))}
            value={form.marca}
          />
          <Input
            label="Tamaño"
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
            label="Tarjeta de circulación"
            onChange={(event) =>
              setForm((current) => ({ ...current, tarjeta_circulacion: event.target.value }))
            }
            value={form.tarjeta_circulacion}
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
            Caja activa
          </label>
        </div>
        <EntityDocumentsSection
          entityId={editingCaja?.id_caja ?? null}
          entityType="CAJA"
        />
        {formError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={submitting || !form.placas.trim()}
            onClick={() => void handleSubmit()}
            type="button"
          >
            {submitting
              ? editingCaja
                ? "Guardando..."
                : "Creando..."
              : editingCaja
                ? "Guardar cambios"
                : "Guardar caja"}
          </Button>
          <Button
            onClick={() => {
              setModalOpen(false);
              setEditingCaja(null);
            }}
            type="button"
            variant="ghost"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Este cambio actualizará el estado de la caja sin borrar su historial."
        onClose={() => {
          if (deleting) return;
          setDeleteModalOpen(false);
          setCajaToToggle(null);
          setDeleteError(null);
        }}
        open={deleteModalOpen}
        title="Confirmar cambio de estado"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            {cajaToToggle
              ? cajaToToggle.activo
                ? `¿Deseas desactivar el registro ${cajaToToggle.numero_economico ?? cajaToToggle.placas}?`
                : `¿Deseas reactivar el registro ${cajaToToggle.numero_economico ?? cajaToToggle.placas}?`
              : "¿Deseas actualizar el estado de esta caja?"}
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
              variant={cajaToToggle?.activo ? "warning" : "success"}
            >
              {deleting
                ? cajaToToggle?.activo
                  ? "Desactivando..."
                  : "Reactivando..."
                : cajaToToggle?.activo
                  ? "Sí, desactivar"
                  : "Sí, reactivar"}
            </Button>
            <Button
              onClick={() => {
                setDeleteModalOpen(false);
                setCajaToToggle(null);
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
