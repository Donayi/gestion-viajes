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
import { ApiError } from "@/services/api-client";
import { getRolesRequest } from "@/services/roles.service";
import {
  changeUsuarioPasswordRequest,
  createUsuarioRequest,
  deleteUsuarioRequest,
  getUsuariosRequest,
  updateUsuarioRequest
} from "@/services/usuarios.service";
import type { Role } from "@/types/role";
import type {
  AdminUser,
  ChangeUserPasswordPayload,
  CreateAdminUserPayload,
  UpdateAdminUserPayload
} from "@/types/user-admin";

type UserFormState = {
  username: string;
  password: string;
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  telefono: string;
  activo: boolean;
  id_rol: string;
};

type PasswordFormState = {
  new_password: string;
  confirm_password: string;
};

const initialForm: UserFormState = {
  username: "",
  password: "",
  nombre: "",
  apellido: "",
  fecha_nacimiento: "",
  telefono: "",
  activo: true,
  id_rol: ""
};

const initialPasswordForm: PasswordFormState = {
  new_password: "",
  confirm_password: ""
};

function toFormState(user: AdminUser | null): UserFormState {
  if (!user) {
    return initialForm;
  }

  return {
    username: user.username,
    password: "",
    nombre: user.nombre,
    apellido: user.apellido,
    fecha_nacimiento: user.fecha_nacimiento ?? "",
    telefono: user.telefono ?? "",
    activo: user.activo,
    id_rol: String(user.id_rol)
  };
}

function buildCreatePayload(form: UserFormState): CreateAdminUserPayload {
  return {
    username: form.username.trim(),
    password: form.password,
    nombre: form.nombre.trim(),
    apellido: form.apellido.trim(),
    fecha_nacimiento: form.fecha_nacimiento || null,
    telefono: form.telefono.trim() || null,
    activo: form.activo,
    id_rol: Number(form.id_rol)
  };
}

function buildUpdatePayload(form: UserFormState): UpdateAdminUserPayload {
  return {
    username: form.username.trim(),
    nombre: form.nombre.trim(),
    apellido: form.apellido.trim(),
    fecha_nacimiento: form.fecha_nacimiento || null,
    telefono: form.telefono.trim() || null,
    activo: form.activo,
    id_rol: Number(form.id_rol)
  };
}

export default function AdminUsuariosPage() {
  const [usuarios, setUsuarios] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [form, setForm] = useState<UserFormState>(initialForm);
  const [passwordForm, setPasswordForm] = useState<PasswordFormState>(initialPasswordForm);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [userToDelete, setUserToDelete] = useState<AdminUser | null>(null);
  const [passwordTarget, setPasswordTarget] = useState<AdminUser | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usuariosData, rolesData] = await Promise.all([getUsuariosRequest(), getRolesRequest()]);
      setUsuarios(usuariosData);
      setRoles(rolesData);
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible cargar los usuarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreateModal() {
    setEditingUser(null);
    setForm(initialForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEditModal(user: AdminUser) {
    setEditingUser(user);
    setForm(toFormState(user));
    setFormError(null);
    setModalOpen(true);
  }

  function openDeleteModal(user: AdminUser) {
    setUserToDelete(user);
    setDeleteError(null);
    setDeleteModalOpen(true);
  }

  function openPasswordModal(user: AdminUser) {
    setPasswordTarget(user);
    setPasswordForm(initialPasswordForm);
    setPasswordError(null);
    setPasswordModalOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);

    try {
      if (editingUser) {
        await updateUsuarioRequest(editingUser.id_usuario, buildUpdatePayload(form));
      } else {
        await createUsuarioRequest(buildCreatePayload(form));
      }

      setModalOpen(false);
      setEditingUser(null);
      setForm(initialForm);
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : editingUser
            ? "No fue posible actualizar el usuario"
            : "No fue posible crear el usuario"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!userToDelete) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      await deleteUsuarioRequest(userToDelete.id_usuario);
      setDeleteModalOpen(false);
      setUserToDelete(null);
      await load();
    } catch (currentError) {
      setDeleteError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible eliminar el usuario"
      );
    } finally {
      setDeleting(false);
    }
  }

  async function handlePasswordChange() {
    if (!passwordTarget) {
      return;
    }

    if (!passwordForm.new_password || !passwordForm.confirm_password) {
      setPasswordError("Debes capturar y confirmar la nueva contraseña");
      return;
    }

    if (passwordForm.new_password.length < 8) {
      setPasswordError("La nueva contraseña debe tener al menos 8 caracteres");
      return;
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError("Las contraseñas no coinciden");
      return;
    }

    setChangingPassword(true);
    setPasswordError(null);

    try {
      const payload: ChangeUserPasswordPayload = {
        new_password: passwordForm.new_password
      };
      await changeUsuarioPasswordRequest(passwordTarget.id_usuario, payload);
      setPasswordModalOpen(false);
      setPasswordTarget(null);
      setPasswordForm(initialPasswordForm);
    } catch (currentError) {
      setPasswordError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible actualizar la contraseña"
      );
    } finally {
      setChangingPassword(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando usuarios..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        description="Da de alta usuarios administrativos y operativos ligados a los roles del sistema."
        eyebrow="Administración"
        title="Usuarios"
      />

      {usuarios.length === 0 ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openCreateModal} type="button">
              Crear usuario
            </Button>
          </div>
          <AdminEmptyState
            description="Crea el primer usuario para administrar o operar viajes desde la aplicación."
            title="No hay usuarios registrados"
          />
        </div>
      ) : (
        <AdminTableShell
          action={
            <Button onClick={openCreateModal} type="button">
              Crear usuario
            </Button>
          }
          title="Listado de usuarios"
        >
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["ID", "Username", "Nombre", "Apellido", "Rol", "Activo", "Teléfono", "Acciones"].map((header) => (
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
              {usuarios.map((usuario) => (
                <tr key={usuario.id_usuario} className="border-t border-slate-100">
                  <td className="px-4 py-4 text-slate-700">{usuario.id_usuario}</td>
                  <td className="px-4 py-4 font-semibold text-slate-950">{usuario.username}</td>
                  <td className="px-4 py-4 text-slate-700">{usuario.nombre}</td>
                  <td className="px-4 py-4 text-slate-700">{usuario.apellido}</td>
                  <td className="px-4 py-4 text-slate-700">
                    {roles.find((role) => role.id_rol === usuario.id_rol)?.nombre ?? usuario.id_rol}
                  </td>
                  <td className="px-4 py-4 text-slate-700">{usuario.activo ? "Sí" : "No"}</td>
                  <td className="px-4 py-4 text-slate-700">{usuario.telefono ?? "Sin dato"}</td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      <Button onClick={() => openEditModal(usuario)} type="button" variant="secondary">
                        Editar
                      </Button>
                      <Button onClick={() => openPasswordModal(usuario)} type="button" variant="secondary">
                        Cambiar contraseña
                      </Button>
                      <Button onClick={() => openDeleteModal(usuario)} type="button" variant="danger">
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
          editingUser
            ? "Actualiza los datos base del usuario seleccionado."
            : "Captura los datos base del nuevo usuario y asígnale un rol."
        }
        onClose={() => {
          if (submitting) return;
          setModalOpen(false);
          setEditingUser(null);
          setFormError(null);
        }}
        open={modalOpen}
        title={editingUser ? "Editar usuario" : "Crear usuario"}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Username"
            onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
            value={form.username}
          />
          {!editingUser ? (
            <Input
              label="Password"
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              type="password"
              value={form.password}
            />
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              La contraseña se cambia desde la acción separada "Cambiar contraseña".
            </div>
          )}
          <Input
            label="Nombre"
            onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))}
            value={form.nombre}
          />
          <Input
            label="Apellido"
            onChange={(event) => setForm((current) => ({ ...current, apellido: event.target.value }))}
            value={form.apellido}
          />
          <Input
            label="Fecha de nacimiento"
            onChange={(event) =>
              setForm((current) => ({ ...current, fecha_nacimiento: event.target.value }))
            }
            type="date"
            value={form.fecha_nacimiento}
          />
          <Input
            label="Teléfono"
            onChange={(event) => setForm((current) => ({ ...current, telefono: event.target.value }))}
            value={form.telefono}
          />
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Rol</span>
            <select
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              onChange={(event) => setForm((current) => ({ ...current, id_rol: event.target.value }))}
              value={form.id_rol}
            >
              <option value="">Selecciona un rol</option>
              {roles.map((role) => (
                <option key={role.id_rol} value={role.id_rol}>
                  {role.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.activo}
              onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))}
              type="checkbox"
            />
            Usuario activo
          </label>
        </div>
        {formError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={
              submitting ||
              !form.username.trim() ||
              !form.nombre.trim() ||
              !form.apellido.trim() ||
              !form.id_rol ||
              (!editingUser && !form.password)
            }
            onClick={() => void handleSubmit()}
            type="button"
          >
            {submitting
              ? editingUser
                ? "Guardando..."
                : "Creando..."
              : editingUser
                ? "Guardar cambios"
                : "Guardar usuario"}
          </Button>
          <Button
            onClick={() => {
              setModalOpen(false);
              setEditingUser(null);
            }}
            type="button"
            variant="secondary"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Captura y confirma la nueva contraseña. Nunca se mostrará ni devolverá al frontend."
        onClose={() => {
          if (changingPassword) return;
          setPasswordModalOpen(false);
          setPasswordTarget(null);
          setPasswordError(null);
          setPasswordForm(initialPasswordForm);
        }}
        open={passwordModalOpen}
        title="Cambiar contraseña"
      >
        <div className="grid gap-4">
          <Input
            label="Nueva contraseña"
            onChange={(event) =>
              setPasswordForm((current) => ({ ...current, new_password: event.target.value }))
            }
            type="password"
            value={passwordForm.new_password}
          />
          <Input
            label="Confirmar nueva contraseña"
            onChange={(event) =>
              setPasswordForm((current) => ({ ...current, confirm_password: event.target.value }))
            }
            type="password"
            value={passwordForm.confirm_password}
          />
        </div>
        {passwordError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {passwordError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={changingPassword || !passwordForm.new_password || !passwordForm.confirm_password}
            onClick={() => void handlePasswordChange()}
            type="button"
          >
            {changingPassword ? "Actualizando..." : "Guardar nueva contraseña"}
          </Button>
          <Button
            onClick={() => {
              setPasswordModalOpen(false);
              setPasswordTarget(null);
              setPasswordError(null);
              setPasswordForm(initialPasswordForm);
            }}
            type="button"
            variant="secondary"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Esta acción eliminará el usuario de forma definitiva si el backend lo permite."
        onClose={() => {
          if (deleting) return;
          setDeleteModalOpen(false);
          setUserToDelete(null);
          setDeleteError(null);
        }}
        open={deleteModalOpen}
        title="Confirmar eliminación"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            {userToDelete
              ? `¿Deseas eliminar al usuario ${userToDelete.username}?`
              : "¿Deseas eliminar este usuario?"}
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
                setUserToDelete(null);
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
