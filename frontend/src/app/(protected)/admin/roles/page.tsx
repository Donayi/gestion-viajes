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
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/services/api-client";
import {
  createRoleRequest,
  deleteRoleRequest,
  getRolesRequest,
  updateRoleRequest
} from "@/services/roles.service";
import type { CreateRolePayload, Role, UpdateRolePayload } from "@/types/role";

type RoleFormState = {
  nombre: string;
  descripcion: string;
};

const initialForm: RoleFormState = {
  nombre: "",
  descripcion: ""
};

function toFormState(role: Role | null): RoleFormState {
  if (!role) {
    return initialForm;
  }

  return {
    nombre: role.nombre,
    descripcion: role.descripcion ?? ""
  };
}

function buildCreatePayload(form: RoleFormState): CreateRolePayload {
  return {
    nombre: form.nombre.trim(),
    descripcion: form.descripcion.trim() || null
  };
}

function buildUpdatePayload(form: RoleFormState): UpdateRolePayload {
  return buildCreatePayload(form);
}

export default function AdminRolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [form, setForm] = useState<RoleFormState>(initialForm);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [roleToDelete, setRoleToDelete] = useState<Role | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRoles(await getRolesRequest());
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible cargar los roles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreateModal() {
    setEditingRole(null);
    setForm(initialForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEditModal(role: Role) {
    setEditingRole(role);
    setForm(toFormState(role));
    setFormError(null);
    setModalOpen(true);
  }

  function openDeleteModal(role: Role) {
    setRoleToDelete(role);
    setDeleteError(null);
    setDeleteModalOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);

    try {
      if (editingRole) {
        await updateRoleRequest(editingRole.id_rol, buildUpdatePayload(form));
      } else {
        await createRoleRequest(buildCreatePayload(form));
      }

      setModalOpen(false);
      setEditingRole(null);
      setForm(initialForm);
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : editingRole
            ? "No fue posible actualizar el rol"
            : "No fue posible crear el rol"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!roleToDelete) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      await deleteRoleRequest(roleToDelete.id_rol);
      setDeleteModalOpen(false);
      setRoleToDelete(null);
      await load();
    } catch (currentError) {
      setDeleteError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible eliminar el rol"
      );
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando roles..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        description="Gestiona los roles base del sistema sin salir de la app administrativa."
        eyebrow="Administración"
        title="Roles"
      />

      {roles.length === 0 ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateModal} type="button">
              Crear rol
            </Button>
          </div>
          <AdminEmptyState
            description="Crea el primer rol operativo para empezar a administrar usuarios."
            title="No hay roles registrados"
          />
        </div>
      ) : (
        <AdminTableShell
          action={
            <Button onClick={openCreateModal} type="button">
              Crear rol
            </Button>
          }
          title="Listado de roles"
        >
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["ID", "Nombre", "Descripción", "Acciones"].map((header) => (
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
              {roles.map((role) => (
                <tr key={role.id_rol} className="border-t border-slate-100">
                  <td className="px-4 py-4 text-slate-700">{role.id_rol}</td>
                  <td className="px-4 py-4 font-semibold text-slate-950">{role.nombre}</td>
                  <td className="px-4 py-4 text-slate-700">{role.descripcion ?? "Sin descripción"}</td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <Button onClick={() => openEditModal(role)} type="button" variant="secondary">
                        Editar
                      </Button>
                      <Button onClick={() => openDeleteModal(role)} type="button" variant="danger">
                        Eliminar
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
          editingRole
            ? "Actualiza el nombre y la descripción del rol seleccionado."
            : "Define el nombre y descripción del nuevo rol."
        }
        onClose={() => {
          if (submitting) return;
          setModalOpen(false);
          setEditingRole(null);
          setFormError(null);
        }}
        open={modalOpen}
        title={editingRole ? "Editar rol" : "Crear rol"}
      >
        <div className="grid gap-4">
          <Input
            label="Nombre"
            onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))}
            value={form.nombre}
          />
          <Textarea
            label="Descripción"
            onChange={(event) => setForm((current) => ({ ...current, descripcion: event.target.value }))}
            value={form.descripcion}
          />
        </div>
        {formError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button disabled={submitting || !form.nombre.trim()} onClick={() => void handleSubmit()} type="button">
            {submitting
              ? editingRole
                ? "Guardando..."
                : "Creando..."
              : editingRole
                ? "Guardar cambios"
                : "Guardar rol"}
          </Button>
          <Button
            onClick={() => {
              setModalOpen(false);
              setEditingRole(null);
            }}
            type="button"
            variant="secondary"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Esta acción eliminará el rol de forma definitiva si el backend lo permite."
        onClose={() => {
          if (deleting) return;
          setDeleteModalOpen(false);
          setRoleToDelete(null);
          setDeleteError(null);
        }}
        open={deleteModalOpen}
        title="Confirmar eliminación"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            {roleToDelete
              ? `¿Deseas eliminar el rol ${roleToDelete.nombre}?`
              : "¿Deseas eliminar este rol?"}
          </p>
          {deleteError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {deleteError}
            </div>
          ) : null}
          <div className="flex gap-3">
            <Button disabled={deleting} onClick={() => void handleDelete()} type="button" variant="danger">
              {deleting ? "Eliminando..." : "Sí, eliminar"}
            </Button>
            <Button
              onClick={() => {
                setDeleteModalOpen(false);
                setRoleToDelete(null);
                setDeleteError(null);
              }}
              type="button"
              variant="secondary"
            >
              Cancelar
            </Button>
          </div>
        </div>
      </AdminModal>
    </div>
  );
}
