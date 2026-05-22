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
import { ApiError } from "@/services/api-client";
import {
  createTelegramDestinatarioRequest,
  deleteTelegramDestinatarioRequest,
  getTelegramDestinatariosRequest,
  notificarAlertasPendientesRequest,
  testTelegramDestinatarioRequest,
  updateTelegramDestinatarioRequest,
} from "@/services/telegram.service";
import type {
  CreateTelegramDestinatarioPayload,
  ProcesarNotificacionesResponse,
  TelegramDestinatario,
} from "@/types/telegram";

type TelegramFormState = {
  nombre: string;
  chat_id: string;
  activo: boolean;
  recibe_documentos: boolean;
  recibe_mantenimiento: boolean;
  recibe_viajes: boolean;
};

const initialForm: TelegramFormState = {
  nombre: "",
  chat_id: "",
  activo: true,
  recibe_documentos: true,
  recibe_mantenimiento: true,
  recibe_viajes: true,
};

function toFormState(destinatario: TelegramDestinatario | null): TelegramFormState {
  if (!destinatario) {
    return initialForm;
  }

  return {
    nombre: destinatario.nombre,
    chat_id: destinatario.chat_id,
    activo: destinatario.activo,
    recibe_documentos: destinatario.recibe_documentos,
    recibe_mantenimiento: destinatario.recibe_mantenimiento,
    recibe_viajes: destinatario.recibe_viajes,
  };
}

function buildPayload(form: TelegramFormState): CreateTelegramDestinatarioPayload {
  return {
    nombre: form.nombre.trim(),
    chat_id: form.chat_id.trim(),
    activo: form.activo,
    recibe_documentos: form.recibe_documentos,
    recibe_mantenimiento: form.recibe_mantenimiento,
    recibe_viajes: form.recibe_viajes,
  };
}

export default function AdminTelegramPage() {
  const [destinatarios, setDestinatarios] = useState<TelegramDestinatario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<TelegramFormState>(initialForm);
  const [editingDestinatario, setEditingDestinatario] = useState<TelegramDestinatario | null>(null);
  const [toggleTarget, setToggleTarget] = useState<TelegramDestinatario | null>(null);
  const [toggleBusy, setToggleBusy] = useState(false);
  const [testBusyId, setTestBusyId] = useState<number | null>(null);
  const [processingPending, setProcessingPending] = useState(false);
  const [processSummary, setProcessSummary] = useState<ProcesarNotificacionesResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDestinatarios(await getTelegramDestinatariosRequest());
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cargar los destinatarios de Telegram"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreateModal() {
    setEditingDestinatario(null);
    setForm(initialForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEditModal(destinatario: TelegramDestinatario) {
    setEditingDestinatario(destinatario);
    setForm(toFormState(destinatario));
    setFormError(null);
    setModalOpen(true);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError(null);
    try {
      if (editingDestinatario) {
        await updateTelegramDestinatarioRequest(editingDestinatario.id_destinatario, buildPayload(form));
      } else {
        await createTelegramDestinatarioRequest(buildPayload(form));
      }
      setModalOpen(false);
      setEditingDestinatario(null);
      setForm(initialForm);
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : editingDestinatario
            ? "No fue posible actualizar el destinatario"
            : "No fue posible crear el destinatario"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleActive() {
    if (!toggleTarget) {
      return;
    }

    setToggleBusy(true);
    setError(null);
    try {
      if (toggleTarget.activo) {
        await deleteTelegramDestinatarioRequest(toggleTarget.id_destinatario);
      } else {
        await updateTelegramDestinatarioRequest(toggleTarget.id_destinatario, { activo: true });
      }
      setToggleTarget(null);
      await load();
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible actualizar el estado del destinatario"
      );
    } finally {
      setToggleBusy(false);
    }
  }

  async function handleTest(destinatarioId: number) {
    setTestBusyId(destinatarioId);
    setError(null);
    try {
      const response = await testTelegramDestinatarioRequest(destinatarioId);
      if (!response.enviado) {
        setError(response.mensaje);
      }
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible enviar la prueba de Telegram"
      );
    } finally {
      setTestBusyId(null);
    }
  }

  async function handleProcesarPendientes() {
    setProcessingPending(true);
    setError(null);
    try {
      setProcessSummary(await notificarAlertasPendientesRequest());
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible procesar las notificaciones pendientes"
      );
    } finally {
      setProcessingPending(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando destinatarios de Telegram..." />;
  }

  if (error && destinatarios.length === 0) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Notificaciones"
        title="Telegram"
        description="Administra destinatarios y prueba el envío de alertas operativas por Telegram."
      />

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {processSummary ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-900">Último procesamiento</p>
          <p className="mt-2 text-sm text-slate-600">
            Evaluadas: {processSummary.alertas_evaluadas} · Enviadas: {processSummary.alertas_enviadas} ·
            Sin destinatario: {processSummary.alertas_sin_destinatario} · Omitidas: {processSummary.alertas_omitidas} ·
            Fallidas: {processSummary.alertas_fallidas}
          </p>
        </div>
      ) : null}

      {destinatarios.length === 0 ? (
        <div className="space-y-4">
          <div className="flex flex-wrap justify-end gap-3">
            <Button onClick={() => void handleProcesarPendientes()} type="button" variant="secondary">
              {processingPending ? "Procesando..." : "Notificar pendientes"}
            </Button>
            <Button onClick={openCreateModal} type="button">
              Agregar destinatario
            </Button>
          </div>
          <AdminEmptyState
            title="No hay destinatarios configurados"
            description="Agrega el primer chat de Telegram para comenzar a enviar notificaciones."
          />
        </div>
      ) : (
        <AdminTableShell
          action={
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => void handleProcesarPendientes()} type="button" variant="secondary">
                {processingPending ? "Procesando..." : "Notificar pendientes"}
              </Button>
              <Button onClick={openCreateModal} type="button">
                Agregar destinatario
              </Button>
            </div>
          }
          title="Destinatarios configurados"
        >
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["Nombre", "Chat ID", "Documentos", "Mantenimiento", "Viajes", "Activo", "Acciones"].map((header) => (
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
              {destinatarios.map((destinatario) => (
                <tr key={destinatario.id_destinatario} className="border-t border-slate-100">
                  <td className="px-4 py-4 font-semibold text-slate-950">{destinatario.nombre}</td>
                  <td className="px-4 py-4 text-slate-700">{destinatario.chat_id}</td>
                  <td className="px-4 py-4">
                    <StatusBadge variant={destinatario.recibe_documentos ? "success" : "inactive"}>
                      {destinatario.recibe_documentos ? "Sí" : "No"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge variant={destinatario.recibe_mantenimiento ? "success" : "inactive"}>
                      {destinatario.recibe_mantenimiento ? "Sí" : "No"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge variant={destinatario.recibe_viajes ? "success" : "inactive"}>
                      {destinatario.recibe_viajes ? "Sí" : "No"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge variant={destinatario.activo ? "active" : "inactive"}>
                      {destinatario.activo ? "Activo" : "Inactivo"}
                    </StatusBadge>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap gap-2">
                      <Button onClick={() => openEditModal(destinatario)} type="button" variant="outline">
                        Editar
                      </Button>
                      <Button
                        onClick={() => void handleTest(destinatario.id_destinatario)}
                        type="button"
                        variant="secondary"
                      >
                        {testBusyId === destinatario.id_destinatario ? "Enviando..." : "Enviar prueba"}
                      </Button>
                      <Button
                        onClick={() => setToggleTarget(destinatario)}
                        type="button"
                        variant={destinatario.activo ? "warning" : "success"}
                      >
                        {destinatario.activo ? "Desactivar" : "Reactivar"}
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
          editingDestinatario
            ? "Actualiza el destinatario y los tipos de notificación que recibe."
            : "Configura un nuevo destinatario de Telegram para el envío de alertas."
        }
        onClose={() => {
          if (submitting) return;
          setModalOpen(false);
          setEditingDestinatario(null);
          setFormError(null);
        }}
        open={modalOpen}
        title={editingDestinatario ? "Editar destinatario" : "Nuevo destinatario"}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Nombre"
            onChange={(event) => setForm((current) => ({ ...current, nombre: event.target.value }))}
            value={form.nombre}
          />
          <Input
            label="Chat ID"
            onChange={(event) => setForm((current) => ({ ...current, chat_id: event.target.value }))}
            value={form.chat_id}
          />
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.recibe_documentos}
              onChange={(event) =>
                setForm((current) => ({ ...current, recibe_documentos: event.target.checked }))
              }
              type="checkbox"
            />
            Recibe documentos
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.recibe_mantenimiento}
              onChange={(event) =>
                setForm((current) => ({ ...current, recibe_mantenimiento: event.target.checked }))
              }
              type="checkbox"
            />
            Recibe mantenimiento
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.recibe_viajes}
              onChange={(event) =>
                setForm((current) => ({ ...current, recibe_viajes: event.target.checked }))
              }
              type="checkbox"
            />
            Recibe viajes
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
            <input
              checked={form.activo}
              onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))}
              type="checkbox"
            />
            Destinatario activo
          </label>
        </div>
        {formError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={submitting || !form.nombre.trim() || !form.chat_id.trim()}
            onClick={() => void handleSubmit()}
            type="button"
          >
            {submitting
              ? editingDestinatario
                ? "Guardando..."
                : "Creando..."
              : editingDestinatario
                ? "Guardar cambios"
                : "Guardar destinatario"}
          </Button>
          <Button
            onClick={() => {
              setModalOpen(false);
              setEditingDestinatario(null);
              setFormError(null);
            }}
            type="button"
            variant="ghost"
          >
            Cancelar
          </Button>
        </div>
      </AdminModal>

      <AdminModal
        description="Este cambio solo actualiza el estado del destinatario; no borra historial ni configuración."
        onClose={() => {
          if (toggleBusy) return;
          setToggleTarget(null);
        }}
        open={toggleTarget !== null}
        title="Confirmar cambio de estado"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-700">
            {toggleTarget?.activo
              ? `¿Deseas desactivar a ${toggleTarget.nombre}?`
              : `¿Deseas reactivar a ${toggleTarget?.nombre}?`}
          </p>
          <div className="flex gap-3">
            <Button
              disabled={toggleBusy}
              onClick={() => void handleToggleActive()}
              type="button"
              variant={toggleTarget?.activo ? "warning" : "success"}
            >
              {toggleBusy
                ? toggleTarget?.activo
                  ? "Desactivando..."
                  : "Reactivando..."
                : toggleTarget?.activo
                  ? "Sí, desactivar"
                  : "Sí, reactivar"}
            </Button>
            <Button onClick={() => setToggleTarget(null)} type="button" variant="ghost">
              Cancelar
            </Button>
          </div>
        </div>
      </AdminModal>
    </div>
  );
}
