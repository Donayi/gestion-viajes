"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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
  createOperadorRequest,
  getOperadoresRequest,
  updateOperadorRequest
} from "@/services/operadores.service";
import { getUsuariosRequest } from "@/services/usuarios.service";
import type { Operador, CreateOperadorPayload, UpdateOperadorPayload } from "@/types/operador";
import type { AdminUser } from "@/types/user-admin";

type OperadorFormState = {
  id_usuario: string;
  alias: string;
  rfc: string;
  curp: string;
  numero_licencia: string;
  licencia_vigencia: string;
  sua: string;
  sua_vigencia: string;
  estudio_medico: string;
  numero_expediente_medico: string;
  activo: boolean;
};

const initialForm: OperadorFormState = {
  id_usuario: "",
  alias: "",
  rfc: "",
  curp: "",
  numero_licencia: "",
  licencia_vigencia: "",
  sua: "",
  sua_vigencia: "",
  estudio_medico: "",
  numero_expediente_medico: "",
  activo: true
};

function toFormState(operador: Operador | null): OperadorFormState {
  if (!operador) {
    return initialForm;
  }

  return {
    id_usuario: String(operador.id_usuario),
    alias: operador.alias,
    rfc: operador.rfc ?? "",
    curp: operador.curp ?? "",
    numero_licencia: operador.numero_licencia ?? "",
    licencia_vigencia: operador.licencia_vigencia ?? "",
    sua: operador.sua ?? "",
    sua_vigencia: operador.sua_vigencia ?? "",
    estudio_medico: operador.estudio_medico ?? "",
    numero_expediente_medico: operador.numero_expediente_medico ?? "",
    activo: operador.activo
  };
}

function buildCreatePayload(form: OperadorFormState): CreateOperadorPayload {
  return {
    id_usuario: Number(form.id_usuario),
    alias: form.alias.trim(),
    rfc: form.rfc.trim() || null,
    curp: form.curp.trim() || null,
    numero_licencia: form.numero_licencia.trim() || null,
    licencia_vigencia: form.licencia_vigencia || null,
    sua: form.sua.trim() || null,
    sua_vigencia: form.sua_vigencia || null,
    estudio_medico: form.estudio_medico || null,
    numero_expediente_medico: form.numero_expediente_medico.trim() || null,
    activo: form.activo
  };
}

function buildUpdatePayload(form: OperadorFormState): UpdateOperadorPayload {
  return buildCreatePayload(form);
}

export default function AdminOperadoresPage() {
  const [operadores, setOperadores] = useState<Operador[]>([]);
  const [usuarios, setUsuarios] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [form, setForm] = useState<OperadorFormState>(initialForm);
  const [editingOperador, setEditingOperador] = useState<Operador | null>(null);
  const [operadorToToggle, setOperadorToToggle] = useState<Operador | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [operadoresData, usuariosData] = await Promise.all([
        getOperadoresRequest(),
        getUsuariosRequest()
      ]);
      setOperadores(operadoresData);
      setUsuarios(usuariosData);
    } catch (currentError) {
      setError(
        currentError instanceof ApiError ? currentError.message : "No fue posible cargar los operadores"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const usuariosDisponibles = useMemo(() => {
    const ocupados = new Set(
      operadores
        .filter((operador) => operador.id_operador !== editingOperador?.id_operador)
        .map((operador) => operador.id_usuario)
    );
    return usuarios.filter((usuario) => !ocupados.has(usuario.id_usuario));
  }, [editingOperador?.id_operador, operadores, usuarios]);

  function openCreateModal() {
    setEditingOperador(null);
    setForm(initialForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEditModal(operador: Operador) {
    setEditingOperador(operador);
    setForm(toFormState(operador));
    setFormError(null);
    setModalOpen(true);
  }

  function openDeleteModal(operador: Operador) {
    setOperadorToToggle(operador);
    setDeleteError(null);
    setDeleteModalOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);

    try {
      if (editingOperador) {
        await updateOperadorRequest(editingOperador.id_operador, buildUpdatePayload(form));
      } else {
        await createOperadorRequest(buildCreatePayload(form));
      }

      setModalOpen(false);
      setEditingOperador(null);
      setForm(initialForm);
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : editingOperador
            ? "No fue posible actualizar el operador"
            : "No fue posible crear el operador"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!operadorToToggle) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      await updateOperadorRequest(operadorToToggle.id_operador, { activo: !operadorToToggle.activo });
      setDeleteModalOpen(false);
      setOperadorToToggle(null);
      await load();
    } catch (currentError) {
      setDeleteError(
        currentError instanceof ApiError
          ? currentError.message
          : operadorToToggle.activo
            ? "No fue posible desactivar el operador"
            : "No fue posible reactivar el operador"
      );
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando operadores..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        description="Asocia usuarios a perfiles operativos para que puedan operar viajes desde la app."
        eyebrow="Administración"
        title="Operadores"
      />

      {operadores.length === 0 ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateModal} type="button">
              Crear operador
            </Button>
          </div>
          <AdminEmptyState
            description="Crea el primer operador vinculando un usuario existente."
            title="No hay operadores registrados"
          />
        </div>
      ) : (
        <AdminTableShell
          action={
            <Button onClick={openCreateModal} type="button">
              Crear operador
            </Button>
          }
          title="Listado de operadores"
        >
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["ID", "Usuario", "Alias", "Licencia", "Activo", "SUA", "Acciones"].map((header) => (
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
              {operadores.map((operador) => (
                <tr key={operador.id_operador} className="border-t border-slate-100">
                  <td className="px-4 py-4 text-slate-700">{operador.id_operador}</td>
                  <td className="px-4 py-4 text-slate-700">
                    {usuarios.find((usuario) => usuario.id_usuario === operador.id_usuario)?.username ??
                      operador.id_usuario}
                  </td>
                  <td className="px-4 py-4 font-semibold text-slate-950">{operador.alias}</td>
                  <td className="px-4 py-4 text-slate-700">{operador.numero_licencia ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">
                    <StatusBadge variant={operador.activo ? "active" : "inactive"}>
                      {operador.activo ? "Activo" : "Inactivo"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4 text-slate-700">{operador.sua ?? "Sin dato"}</td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <Button onClick={() => openEditModal(operador)} type="button" variant="outline">
                        Editar
                      </Button>
                      <Button
                        onClick={() => openDeleteModal(operador)}
                        type="button"
                        variant={operador.activo ? "warning" : "success"}
                      >
                        {operador.activo ? "Desactivar" : "Reactivar"}
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
          editingOperador
            ? "Actualiza la información del operador seleccionado."
            : "Vincula un usuario existente y completa los datos base del operador."
        }
        onClose={() => {
          if (submitting) return;
          setModalOpen(false);
          setEditingOperador(null);
          setFormError(null);
        }}
        open={modalOpen}
        title={editingOperador ? "Editar operador" : "Crear operador"}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-2 md:col-span-2">
            <span className="text-sm font-medium text-slate-700">Usuario</span>
            <select
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              onChange={(event) => setForm((current) => ({ ...current, id_usuario: event.target.value }))}
              value={form.id_usuario}
            >
              <option value="">Selecciona un usuario</option>
              {usuariosDisponibles.map((usuario) => (
                <option key={usuario.id_usuario} value={usuario.id_usuario}>
                  {usuario.username} · {usuario.nombre} {usuario.apellido}
                </option>
              ))}
            </select>
          </label>

          <Input
            label="Alias"
            onChange={(event) => setForm((current) => ({ ...current, alias: event.target.value }))}
            value={form.alias}
          />
          <Input
            label="RFC"
            onChange={(event) => setForm((current) => ({ ...current, rfc: event.target.value }))}
            value={form.rfc}
          />
          <Input
            label="CURP"
            onChange={(event) => setForm((current) => ({ ...current, curp: event.target.value }))}
            value={form.curp}
          />

          <Input
            label="Número de licencia"
            onChange={(event) =>
              setForm((current) => ({ ...current, numero_licencia: event.target.value }))
            }
            value={form.numero_licencia}
          />
          <Input
            label="Vigencia licencia"
            onChange={(event) =>
              setForm((current) => ({ ...current, licencia_vigencia: event.target.value }))
            }
            type="date"
            value={form.licencia_vigencia}
          />

          <Input
            label="SUA"
            onChange={(event) => setForm((current) => ({ ...current, sua: event.target.value }))}
            value={form.sua}
          />
          <Input
            label="Vigencia SUA"
            onChange={(event) => setForm((current) => ({ ...current, sua_vigencia: event.target.value }))}
            type="date"
            value={form.sua_vigencia}
          />

          <Input
            label="Estudio médico"
            onChange={(event) =>
              setForm((current) => ({ ...current, estudio_medico: event.target.value }))
            }
            type="date"
            value={form.estudio_medico}
          />
          <Input
            label="Número de expediente médico"
            onChange={(event) =>
              setForm((current) => ({ ...current, numero_expediente_medico: event.target.value }))
            }
            value={form.numero_expediente_medico}
          />

          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.activo}
              onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))}
              type="checkbox"
            />
            Operador activo
          </label>
        </div>
        <EntityDocumentsSection
          entityId={editingOperador?.id_operador ?? null}
          entityType="OPERADOR"
        />
        {formError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={submitting || !form.id_usuario || !form.alias.trim()}
            onClick={() => void handleSubmit()}
            type="button"
          >
            {submitting
              ? editingOperador
                ? "Guardando..."
                : "Creando..."
              : editingOperador
                ? "Guardar cambios"
                : "Guardar operador"}
          </Button>
          <Button
            onClick={() => {
              setModalOpen(false);
              setEditingOperador(null);
            }}
            type="button"
            variant="ghost"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Este cambio actualizará el estado del operador sin borrar su historial."
        onClose={() => {
          if (deleting) return;
          setDeleteModalOpen(false);
          setOperadorToToggle(null);
          setDeleteError(null);
        }}
        open={deleteModalOpen}
        title="Confirmar cambio de estado"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            {operadorToToggle
              ? operadorToToggle.activo
                ? `¿Deseas desactivar el registro ${operadorToToggle.alias}?`
                : `¿Deseas reactivar el registro ${operadorToToggle.alias}?`
              : "¿Deseas actualizar el estado de este operador?"}
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
              variant={operadorToToggle?.activo ? "warning" : "success"}
            >
              {deleting
                ? operadorToToggle?.activo
                  ? "Desactivando..."
                  : "Reactivando..."
                : operadorToToggle?.activo
                  ? "Sí, desactivar"
                  : "Sí, reactivar"}
            </Button>
            <Button
              onClick={() => {
                setDeleteModalOpen(false);
                setOperadorToToggle(null);
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
