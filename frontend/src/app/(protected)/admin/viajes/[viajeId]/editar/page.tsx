"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminEmptyState } from "@/components/admin/admin-empty-state";
import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { LocationPicker } from "@/components/viajes/location-picker";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { Textarea } from "@/components/ui/textarea";
import { useSession } from "@/hooks/use-session";
import { ApiError } from "@/services/api-client";
import { getClientesRequest } from "@/services/clientes.service";
import {
  asignarViajeRequest,
  getCajasDisponiblesRequest,
  getOperadoresDisponiblesRequest,
  getTrailersDisponiblesRequest,
  getViajeDetailRequest,
  reasignarViajeRequest,
  updateViajeRequest
} from "@/services/viajes.service";
import type { Cliente } from "@/types/cliente";
import type {
  CajaDisponible,
  OperadorDisponible,
  TrailerDisponible,
  ViajeDetail,
  ViajeUpdatePayload
} from "@/types/viaje";

type ViajeEditFormState = {
  folio: string;
  folio_viaje_cliente: string;
  id_cliente: string;
  lugar_inicio: string;
  lugar_destino: string;
  lugar_inicio_latitud: number | null;
  lugar_inicio_longitud: number | null;
  lugar_destino_latitud: number | null;
  lugar_destino_longitud: number | null;
  tipo_carga: string;
  descripcion_carga: string;
  fecha_programada_salida: string;
  fecha_carga: string;
  hora_carga: string;
  fecha_descarga: string;
  hora_descarga: string;
  fecha_entrega: string;
  hora_entrega: string;
  hora_cita_descarga: string;
  observaciones: string;
};

type AssignmentFormState = {
  id_operador: string;
  id_trailer: string;
  id_caja: string;
  motivo: string;
  comentario: string;
};

const initialAssignmentForm: AssignmentFormState = {
  id_operador: "",
  id_trailer: "",
  id_caja: "",
  motivo: "",
  comentario: ""
};

function asDatetimeLocalValue(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function toFormState(viaje: ViajeDetail): ViajeEditFormState {
  return {
    folio: viaje.folio,
    folio_viaje_cliente: viaje.folio_viaje_cliente ?? "",
    id_cliente: String(viaje.id_cliente),
    lugar_inicio: viaje.lugar_inicio,
    lugar_destino: viaje.lugar_destino,
    lugar_inicio_latitud: viaje.lugar_inicio_latitud,
    lugar_inicio_longitud: viaje.lugar_inicio_longitud,
    lugar_destino_latitud: viaje.lugar_destino_latitud,
    lugar_destino_longitud: viaje.lugar_destino_longitud,
    tipo_carga: viaje.tipo_carga ?? "",
    descripcion_carga: viaje.descripcion_carga ?? "",
    fecha_programada_salida: asDatetimeLocalValue(viaje.fecha_programada_salida),
    fecha_carga: viaje.fecha_carga ?? "",
    hora_carga: viaje.hora_carga ?? "",
    fecha_descarga: viaje.fecha_descarga ?? "",
    hora_descarga: viaje.hora_descarga ?? "",
    fecha_entrega: viaje.fecha_entrega ?? "",
    hora_entrega: viaje.hora_entrega ?? "",
    hora_cita_descarga: viaje.hora_cita_descarga ?? "",
    observaciones: viaje.observaciones ?? ""
  };
}

function buildUpdatePayload(
  form: ViajeEditFormState,
  updatedBy: number | null | undefined
): ViajeUpdatePayload {
  return {
    folio_viaje_cliente: form.folio_viaje_cliente.trim() || null,
    id_cliente: Number(form.id_cliente),
    lugar_inicio: form.lugar_inicio.trim(),
    lugar_destino: form.lugar_destino.trim(),
    lugar_inicio_latitud: form.lugar_inicio_latitud,
    lugar_inicio_longitud: form.lugar_inicio_longitud,
    lugar_destino_latitud: form.lugar_destino_latitud,
    lugar_destino_longitud: form.lugar_destino_longitud,
    tipo_carga: form.tipo_carga.trim() || null,
    descripcion_carga: form.descripcion_carga.trim() || null,
    fecha_programada_salida: form.fecha_programada_salida || null,
    fecha_carga: form.fecha_carga || null,
    hora_carga: form.hora_carga || null,
    fecha_descarga: form.fecha_descarga || null,
    hora_descarga: form.hora_descarga || null,
    fecha_entrega: form.fecha_descarga || null,
    hora_entrega: form.hora_descarga || null,
    hora_cita_descarga: form.hora_descarga || null,
    observaciones: form.observaciones.trim() || null,
    updated_by: updatedBy ?? null
  };
}

export default function AdminEditarViajePage() {
  const params = useParams<{ viajeId: string }>();
  const viajeId = Number(params.viajeId);
  const router = useRouter();
  const { user } = useSession();

  const [detail, setDetail] = useState<ViajeDetail | null>(null);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [operadores, setOperadores] = useState<OperadorDisponible[]>([]);
  const [trailers, setTrailers] = useState<TrailerDisponible[]>([]);
  const [cajas, setCajas] = useState<CajaDisponible[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [form, setForm] = useState<ViajeEditFormState | null>(null);
  const [assignmentForm, setAssignmentForm] = useState<AssignmentFormState>(initialAssignmentForm);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [detailData, clientesData, operadoresData, trailersData, cajasData] = await Promise.all([
        getViajeDetailRequest(viajeId),
        getClientesRequest(),
        getOperadoresDisponiblesRequest(),
        getTrailersDisponiblesRequest(),
        getCajasDisponiblesRequest()
      ]);

      setDetail(detailData);
      setForm(toFormState(detailData));
      setClientes(clientesData);
      setOperadores(operadoresData);
      setTrailers(trailersData);
      setCajas(cajasData);
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cargar la edición administrativa del viaje"
      );
    } finally {
      setLoading(false);
    }
  }, [viajeId]);

  useEffect(() => {
    void load();
  }, [load]);

  const canAssignLater = useMemo(() => {
    if (!detail) return false;
    return detail.estatus_actual.clave === "CREADO" && !detail.id_operador_actual && !detail.id_trailer_actual;
  }, [detail]);

  const canReassignAdministrative = useMemo(
    () => detail?.estatus_actual.clave === "STANDBY" || detail?.estatus_actual.clave === "ASIGNADO",
    [detail]
  );
  const isFinalizado = useMemo(
    () => detail?.estatus_actual.clave === "FINALIZADO" || detail?.estatus_actual.clave === "CANCELADO",
    [detail]
  );

  const shouldPreserveCurrentCaja = useMemo(
    () => detail?.estatus_actual.clave === "STANDBY" && Boolean(detail?.caja_actual),
    [detail]
  );

  const currentCajaLabel = useMemo(() => {
    if (!detail?.caja_actual) return null;
    const numeroEconomico = detail.caja_actual.numero_economico ?? "Caja sin número";
    return `${numeroEconomico} · ${detail.caja_actual.placas}`;
  }, [detail]);

  async function handleSave() {
    if (!form) return;

    setSaving(true);
    setFormError(null);
    setSuccessMessage(null);

    try {
      await updateViajeRequest(viajeId, buildUpdatePayload(form, user?.id_usuario));
      await load();
      setSuccessMessage("Datos administrativos del viaje actualizados correctamente.");
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible actualizar el viaje"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleAssignment() {
    if (!detail) return;

    setAssigning(true);
    setAssignError(null);

    try {
      const payload = {
        id_operador: Number(assignmentForm.id_operador),
        id_trailer: Number(assignmentForm.id_trailer),
        id_caja: shouldPreserveCurrentCaja
          ? detail.caja_actual?.id_caja ?? null
          : assignmentForm.id_caja
            ? Number(assignmentForm.id_caja)
            : null,
        created_by: user?.id_usuario ?? null,
        motivo: assignmentForm.motivo.trim() || null,
        comentario: assignmentForm.comentario.trim() || null
      };

      if (canReassignAdministrative) {
        await reasignarViajeRequest(viajeId, payload);
      } else {
        await asignarViajeRequest(viajeId, payload);
      }

      router.push(`/viajes/${viajeId}`);
    } catch (currentError) {
      setAssignError(
          currentError instanceof ApiError
          ? currentError.message
          : canReassignAdministrative
            ? "No fue posible reasignar el viaje"
            : "No fue posible asignar el viaje"
      );
    } finally {
      setAssigning(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando edición del viaje..." />;
  }

  if (error || !detail || !form) {
    return <ErrorState message={error ?? "No fue posible cargar el viaje"} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Administración"
        title={`Editar viaje ${detail.folio}`}
        description="Edita los datos administrativos del viaje sin alterar el workflow controlado de estatus."
      />

      <div className="flex flex-wrap gap-3">
        <Link
          className="inline-flex items-center justify-center rounded-2xl bg-slate-100 px-4 py-3 text-sm font-medium text-slate-900"
          href={`/viajes/${detail.id_viaje}`}
        >
          Volver al detalle
        </Link>
      </div>

      {canReassignAdministrative ? (
        <div className="rounded-[1.5rem] border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
          Reasignación administrativa por corrección.
        </div>
      ) : null}
      {isFinalizado ? (
        <div className="rounded-[1.5rem] border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-900">
          Este viaje está finalizado y no admite modificaciones operativas.
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <section className="rounded-[2rem] border border-brand-100 bg-white p-6 shadow-soft">
          <h2 className="text-2xl font-semibold text-slate-950">Datos administrativos</h2>
          <p className="mt-2 text-sm text-slate-600">
            {isFinalizado
              ? "Este viaje finalizado se muestra en modo consulta administrativa."
              : "Este formulario no cambia estatus ni recursos actuales del viaje."}
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-sm font-medium text-slate-700">Folio interno</p>
              <p className="mt-1 text-sm text-slate-950">{form.folio}</p>
              <p className="mt-2 text-xs text-slate-500">Este folio lo genera el sistema y no es editable.</p>
            </div>
            <Input
              label="Folio del cliente"
              onChange={(event) =>
                setForm((current) => current ? { ...current, folio_viaje_cliente: event.target.value } : current)
              }
              value={form.folio_viaje_cliente}
            />
            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Cliente</span>
              <select
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                onChange={(event) =>
                  setForm((current) => current ? { ...current, id_cliente: event.target.value } : current)
                }
                value={form.id_cliente}
              >
                <option value="">Selecciona un cliente</option>
                {clientes.map((cliente) => (
                  <option key={cliente.id_cliente} value={cliente.id_cliente}>
                    {cliente.nombre_razon_social}
                  </option>
                ))}
              </select>
            </label>
            <div className="md:col-span-2">
              <LocationPicker
                address={form.lugar_inicio}
                label="Ubicación de inicio"
                latitude={form.lugar_inicio_latitud}
                longitude={form.lugar_inicio_longitud}
                onAddressChange={(value) =>
                  setForm((current) => (current ? { ...current, lugar_inicio: value } : current))
                }
                onCoordinatesChange={({ latitud, longitud }) =>
                  setForm((current) =>
                    current
                      ? {
                          ...current,
                          lugar_inicio_latitud: latitud,
                          lugar_inicio_longitud: longitud,
                        }
                      : current
                  )
                }
              />
            </div>
            <div className="md:col-span-2">
              <LocationPicker
                address={form.lugar_destino}
                label="Ubicación de destino"
                latitude={form.lugar_destino_latitud}
                longitude={form.lugar_destino_longitud}
                onAddressChange={(value) =>
                  setForm((current) => (current ? { ...current, lugar_destino: value } : current))
                }
                onCoordinatesChange={({ latitud, longitud }) =>
                  setForm((current) =>
                    current
                      ? {
                          ...current,
                          lugar_destino_latitud: latitud,
                          lugar_destino_longitud: longitud,
                        }
                      : current
                  )
                }
              />
            </div>
            <Input
              label="Tipo de carga"
              onChange={(event) =>
                setForm((current) => current ? { ...current, tipo_carga: event.target.value } : current)
              }
              value={form.tipo_carga}
            />
            <Input
              label="Fecha programada de salida"
              onChange={(event) =>
                setForm((current) =>
                  current ? { ...current, fecha_programada_salida: event.target.value } : current
                )
              }
              type="datetime-local"
              value={form.fecha_programada_salida}
            />
            <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">Cita de carga</p>
              <div className="mt-3 grid gap-4 md:grid-cols-2">
                <Input
                  label="Fecha de carga"
                  onChange={(event) =>
                    setForm((current) => current ? { ...current, fecha_carga: event.target.value } : current)
                  }
                  type="date"
                  value={form.fecha_carga}
                />
                <Input
                  label="Hora de carga"
                  onChange={(event) =>
                    setForm((current) => current ? { ...current, hora_carga: event.target.value } : current)
                  }
                  type="time"
                  value={form.hora_carga}
                />
              </div>
            </div>
            <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">Cita de descarga</p>
              <div className="mt-3 grid gap-4 md:grid-cols-2">
                <Input
                  label="Fecha de descarga"
                  onChange={(event) =>
                    setForm((current) => current ? { ...current, fecha_descarga: event.target.value } : current)
                  }
                  type="date"
                  value={form.fecha_descarga}
                />
                <Input
                  label="Hora de descarga"
                  onChange={(event) =>
                    setForm((current) => current ? { ...current, hora_descarga: event.target.value } : current)
                  }
                  type="time"
                  value={form.hora_descarga}
                />
              </div>
            </div>
            <div className="md:col-span-2">
              <Textarea
                label="Descripción de carga"
                onChange={(event) =>
                  setForm((current) =>
                    current ? { ...current, descripcion_carga: event.target.value } : current
                  )
                }
                value={form.descripcion_carga}
              />
            </div>
            <div className="md:col-span-2">
              <Textarea
                label="Observaciones"
                onChange={(event) =>
                  setForm((current) => current ? { ...current, observaciones: event.target.value } : current)
                }
                value={form.observaciones}
              />
            </div>
          </div>

          {formError ? (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {formError}
            </div>
          ) : null}

          {successMessage ? (
            <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {successMessage}
            </div>
          ) : null}

          <div className="mt-6 flex flex-wrap gap-3">
            {isFinalizado ? null : (
              <Button
                disabled={saving || !form.id_cliente || !form.lugar_inicio.trim() || !form.lugar_destino.trim()}
                onClick={() => void handleSave()}
                type="button"
              >
                {saving ? "Guardando..." : "Guardar cambios"}
              </Button>
            )}
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-2xl font-semibold text-slate-950">
            {canReassignAdministrative ? "Reasignación administrativa" : "Asignación pendiente"}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {canReassignAdministrative
              ? "Selecciona nuevos recursos para corregir la asignación administrativa sin romper historial ni disponibilidad."
              : "Si el viaje sigue en creado sin recursos actuales, puedes asignarlo después desde aquí."}
          </p>

          {isFinalizado ? (
            <div className="mt-6">
              <AdminEmptyState
                title="Viaje finalizado"
                description="No se puede asignar ni reasignar un viaje finalizado."
              />
            </div>
          ) : !(canAssignLater || canReassignAdministrative) ? (
            <div className="mt-6">
              <AdminEmptyState
                title="Sin reasignación pendiente"
                description="Solo se permite reasignación administrativa segura en viajes CREADO, ASIGNADO o STANDBY."
              />
            </div>
          ) : (
            <>
              <div className="mt-6 grid gap-4">
                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Operador</span>
                  <select
                    className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                    onChange={(event) =>
                      setAssignmentForm((current) => ({ ...current, id_operador: event.target.value }))
                    }
                    value={assignmentForm.id_operador}
                  >
                    <option value="">Selecciona un operador disponible</option>
                    {operadores.map((operador) => (
                      <option key={operador.id_operador} value={operador.id_operador}>
                        {operador.alias}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Tráiler</span>
                  <select
                    className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                    onChange={(event) =>
                      setAssignmentForm((current) => ({ ...current, id_trailer: event.target.value }))
                    }
                    value={assignmentForm.id_trailer}
                  >
                    <option value="">Selecciona un tráiler disponible</option>
                    {trailers.map((trailer) => (
                      <option key={trailer.id_trailer} value={trailer.id_trailer}>
                        {trailer.numero_economico} · {trailer.placas}
                      </option>
                    ))}
                  </select>
                </label>

                {shouldPreserveCurrentCaja ? (
                  <div className="rounded-3xl border border-brand-100 bg-brand-50/70 px-4 py-4">
                    <p className="text-sm font-medium text-brand-900">Caja actual del viaje</p>
                    <p className="mt-1 text-sm text-slate-700">{currentCajaLabel}</p>
                    <p className="mt-2 text-xs text-slate-600">
                      Esta caja permanece ligada al viaje durante standby y se conservará al reasignar.
                    </p>
                  </div>
                ) : (
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-slate-700">Caja</span>
                    <select
                      className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                      onChange={(event) =>
                        setAssignmentForm((current) => ({ ...current, id_caja: event.target.value }))
                      }
                      value={assignmentForm.id_caja}
                    >
                      <option value="">Sin caja</option>
                      {cajas.map((caja) => (
                        <option key={caja.id_caja} value={caja.id_caja}>
                          {(caja.numero_economico ?? "Caja sin número")} · {caja.placas}
                        </option>
                      ))}
                    </select>
                  </label>
                )}

                <Input
                  label="Motivo"
                  onChange={(event) =>
                    setAssignmentForm((current) => ({ ...current, motivo: event.target.value }))
                  }
                  value={assignmentForm.motivo}
                />
                <Textarea
                  label="Comentario"
                  onChange={(event) =>
                    setAssignmentForm((current) => ({ ...current, comentario: event.target.value }))
                  }
                  value={assignmentForm.comentario}
                />
              </div>

              {assignError ? (
                <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {assignError}
                </div>
              ) : null}

              <div className="mt-6 flex flex-wrap gap-3">
                <Button
                  disabled={assigning || !assignmentForm.id_operador || !assignmentForm.id_trailer}
                  onClick={() => void handleAssignment()}
                  type="button"
                >
                  {assigning
                    ? canReassignAdministrative
                      ? "Reasignando..."
                      : "Asignando..."
                    : canReassignAdministrative
                      ? "Reasignar viaje"
                      : "Asignar viaje"}
                </Button>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
