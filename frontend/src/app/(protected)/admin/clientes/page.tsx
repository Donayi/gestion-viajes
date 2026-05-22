"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminEmptyState } from "@/components/admin/admin-empty-state";
import { AdminModal } from "@/components/admin/admin-modal";
import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AdminTableShell } from "@/components/admin/admin-table-shell";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/services/api-client";
import {
  createClienteRequest,
  getClientesRequest,
  updateClienteRequest
} from "@/services/clientes.service";
import type { Cliente, CreateClientePayload, UpdateClientePayload } from "@/types/cliente";

type ClienteFormState = {
  nombre_razon_social: string;
  rfc: string;
  direccion: string;
  cp: string;
  regimen_fiscal: string;
  tiempo_credito: string;
  contacto_nombre: string;
  contacto_telefono: string;
  contacto_email: string;
  activo: boolean;
};

const initialForm: ClienteFormState = {
  nombre_razon_social: "",
  rfc: "",
  direccion: "",
  cp: "",
  regimen_fiscal: "",
  tiempo_credito: "",
  contacto_nombre: "",
  contacto_telefono: "",
  contacto_email: "",
  activo: true
};

function toFormState(cliente: Cliente | null): ClienteFormState {
  if (!cliente) {
    return initialForm;
  }

  return {
    nombre_razon_social: cliente.nombre_razon_social,
    rfc: cliente.rfc ?? "",
    direccion: cliente.direccion ?? "",
    cp: cliente.cp ?? "",
    regimen_fiscal: cliente.regimen_fiscal ?? "",
    tiempo_credito: cliente.tiempo_credito !== null ? String(cliente.tiempo_credito) : "",
    contacto_nombre: cliente.contacto_nombre ?? "",
    contacto_telefono: cliente.contacto_telefono ?? "",
    contacto_email: cliente.contacto_email ?? "",
    activo: cliente.activo
  };
}

function buildCreatePayload(form: ClienteFormState): CreateClientePayload {
  return {
    nombre_razon_social: form.nombre_razon_social.trim(),
    rfc: form.rfc.trim() || null,
    direccion: form.direccion.trim() || null,
    cp: form.cp.trim() || null,
    regimen_fiscal: form.regimen_fiscal.trim() || null,
    tiempo_credito: form.tiempo_credito ? Number(form.tiempo_credito) : null,
    contacto_nombre: form.contacto_nombre.trim() || null,
    contacto_telefono: form.contacto_telefono.trim() || null,
    contacto_email: form.contacto_email.trim() || null,
    activo: form.activo
  };
}

function buildUpdatePayload(form: ClienteFormState): UpdateClientePayload {
  return buildCreatePayload(form);
}

export default function AdminClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [form, setForm] = useState<ClienteFormState>(initialForm);
  const [editingCliente, setEditingCliente] = useState<Cliente | null>(null);
  const [clienteToToggle, setClienteToToggle] = useState<Cliente | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setClientes(await getClientesRequest());
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible cargar los clientes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreateModal() {
    setEditingCliente(null);
    setForm(initialForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEditModal(cliente: Cliente) {
    setEditingCliente(cliente);
    setForm(toFormState(cliente));
    setFormError(null);
    setModalOpen(true);
  }

  function openDeleteModal(cliente: Cliente) {
    setClienteToToggle(cliente);
    setDeleteError(null);
    setDeleteModalOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);

    try {
      if (editingCliente) {
        await updateClienteRequest(editingCliente.id_cliente, buildUpdatePayload(form));
      } else {
        await createClienteRequest(buildCreatePayload(form));
      }

      setModalOpen(false);
      setEditingCliente(null);
      setForm(initialForm);
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : editingCliente
            ? "No fue posible actualizar el cliente"
            : "No fue posible crear el cliente"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!clienteToToggle) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      await updateClienteRequest(clienteToToggle.id_cliente, { activo: !clienteToToggle.activo });
      setDeleteModalOpen(false);
      setClienteToToggle(null);
      await load();
    } catch (currentError) {
      setDeleteError(
        currentError instanceof ApiError
          ? currentError.message
          : clienteToToggle.activo
            ? "No fue posible desactivar el cliente"
            : "No fue posible reactivar el cliente"
      );
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando clientes..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        description="Administra la base de clientes para programar y operar viajes desde la plataforma."
        eyebrow="Administración"
        title="Clientes"
      />

      {clientes.length === 0 ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateModal} type="button">
              Crear cliente
            </Button>
          </div>
          <AdminEmptyState
            description="Crea el primer cliente operativo para comenzar a registrar viajes."
            title="No hay clientes registrados"
          />
        </div>
      ) : (
        <AdminTableShell
          action={
            <Button onClick={openCreateModal} type="button">
              Crear cliente
            </Button>
          }
          title="Listado de clientes"
        >
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["ID", "Razón social", "RFC", "Crédito", "Contacto", "Activo", "Acciones"].map((header) => (
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
              {clientes.map((cliente) => (
                <tr key={cliente.id_cliente} className="border-t border-slate-100">
                  <td className="px-4 py-4 text-slate-700">{cliente.id_cliente}</td>
                  <td className="px-4 py-4 font-semibold text-slate-950">{cliente.nombre_razon_social}</td>
                  <td className="px-4 py-4 text-slate-700">{cliente.rfc ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">
                    {cliente.tiempo_credito !== null ? `${cliente.tiempo_credito} días` : "Sin dato"}
                  </td>
                  <td className="px-4 py-4 text-slate-700">{cliente.contacto_nombre ?? "Sin dato"}</td>
                  <td className="px-4 py-4 text-slate-700">
                    <StatusBadge variant={cliente.activo ? "active" : "inactive"}>
                      {cliente.activo ? "Activo" : "Inactivo"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <Button onClick={() => openEditModal(cliente)} type="button" variant="outline">
                        Editar
                      </Button>
                      <Button
                        onClick={() => openDeleteModal(cliente)}
                        type="button"
                        variant={cliente.activo ? "warning" : "success"}
                      >
                        {cliente.activo ? "Desactivar" : "Reactivar"}
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
          editingCliente
            ? "Actualiza la información del cliente seleccionado."
            : "Captura la información base del cliente."
        }
        onClose={() => {
          if (submitting) return;
          setModalOpen(false);
          setEditingCliente(null);
          setFormError(null);
        }}
        open={modalOpen}
        title={editingCliente ? "Editar cliente" : "Crear cliente"}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Nombre / razón social"
            onChange={(event) => setForm((current) => ({ ...current, nombre_razon_social: event.target.value }))}
            value={form.nombre_razon_social}
          />
          <Input
            label="RFC"
            onChange={(event) => setForm((current) => ({ ...current, rfc: event.target.value }))}
            value={form.rfc}
          />
          <div className="md:col-span-2">
            <Textarea
              label="Dirección"
              onChange={(event) => setForm((current) => ({ ...current, direccion: event.target.value }))}
              value={form.direccion}
            />
          </div>
          <Input
            label="Código postal"
            onChange={(event) => setForm((current) => ({ ...current, cp: event.target.value }))}
            value={form.cp}
          />
          <Input
            label="Régimen fiscal"
            onChange={(event) => setForm((current) => ({ ...current, regimen_fiscal: event.target.value }))}
            value={form.regimen_fiscal}
          />
          <Input
            label="Tiempo de crédito (días)"
            onChange={(event) => setForm((current) => ({ ...current, tiempo_credito: event.target.value }))}
            type="number"
            value={form.tiempo_credito}
          />
          <Input
            label="Contacto"
            onChange={(event) => setForm((current) => ({ ...current, contacto_nombre: event.target.value }))}
            value={form.contacto_nombre}
          />
          <Input
            label="Teléfono de contacto"
            onChange={(event) => setForm((current) => ({ ...current, contacto_telefono: event.target.value }))}
            value={form.contacto_telefono}
          />
          <Input
            label="Email de contacto"
            onChange={(event) => setForm((current) => ({ ...current, contacto_email: event.target.value }))}
            type="email"
            value={form.contacto_email}
          />
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.activo}
              onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))}
              type="checkbox"
            />
            Cliente activo
          </label>
        </div>
        {formError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={submitting || !form.nombre_razon_social.trim()}
            onClick={() => void handleSubmit()}
            type="button"
          >
            {submitting
              ? editingCliente
                ? "Guardando..."
                : "Creando..."
              : editingCliente
                ? "Guardar cambios"
                : "Guardar cliente"}
          </Button>
          <Button
            onClick={() => {
              setModalOpen(false);
              setEditingCliente(null);
            }}
            type="button"
            variant="ghost"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Este cambio actualizará el estado del cliente sin borrar su historial."
        onClose={() => {
          if (deleting) return;
          setDeleteModalOpen(false);
          setClienteToToggle(null);
          setDeleteError(null);
        }}
        open={deleteModalOpen}
        title="Confirmar cambio de estado"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            {clienteToToggle
              ? clienteToToggle.activo
                ? `¿Deseas desactivar el registro ${clienteToToggle.nombre_razon_social}?`
                : `¿Deseas reactivar el registro ${clienteToToggle.nombre_razon_social}?`
              : "¿Deseas actualizar el estado de este cliente?"}
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
              variant={clienteToToggle?.activo ? "warning" : "success"}
            >
              {deleting
                ? clienteToToggle?.activo
                  ? "Desactivando..."
                  : "Reactivando..."
                : clienteToToggle?.activo
                  ? "Sí, desactivar"
                  : "Sí, reactivar"}
            </Button>
            <Button
              onClick={() => {
                setDeleteModalOpen(false);
                setClienteToToggle(null);
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
