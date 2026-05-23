"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
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
  createViajeRequest,
  getCajasDisponiblesRequest,
  getOperadoresDisponiblesRequest,
  getTrailersDisponiblesRequest
} from "@/services/viajes.service";
import type { CajaDisponible, OperadorDisponible, TrailerDisponible, ViajeRecord } from "@/types/viaje";
import type { Cliente } from "@/types/cliente";

type ViajeFormState = {
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
  hora_cita_descarga: string;
  observaciones: string;
};

type AsignacionFormState = {
  id_operador: string;
  id_trailer: string;
  id_caja: string;
  motivo: string;
  comentario: string;
};

const initialViajeForm: ViajeFormState = {
  folio_viaje_cliente: "",
  id_cliente: "",
  lugar_inicio: "",
  lugar_destino: "",
  lugar_inicio_latitud: null,
  lugar_inicio_longitud: null,
  lugar_destino_latitud: null,
  lugar_destino_longitud: null,
  tipo_carga: "",
  descripcion_carga: "",
  fecha_programada_salida: "",
  fecha_carga: "",
  hora_carga: "",
  fecha_descarga: "",
  hora_descarga: "",
  hora_cita_descarga: "",
  observaciones: ""
};

const initialAsignacionForm: AsignacionFormState = {
  id_operador: "",
  id_trailer: "",
  id_caja: "",
  motivo: "",
  comentario: ""
};

export default function AdminNuevoViajePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useSession();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [operadores, setOperadores] = useState<OperadorDisponible[]>([]);
  const [trailers, setTrailers] = useState<TrailerDisponible[]>([]);
  const [cajas, setCajas] = useState<CajaDisponible[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [viajeForm, setViajeForm] = useState<ViajeFormState>(initialViajeForm);
  const [asignacionForm, setAsignacionForm] = useState<AsignacionFormState>(initialAsignacionForm);
  const [createdViaje, setCreatedViaje] = useState<ViajeRecord | null>(null);

  const loadCatalogos = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [clientesData, operadoresData, trailersData, cajasData] = await Promise.all([
        getClientesRequest(),
        getOperadoresDisponiblesRequest(),
        getTrailersDisponiblesRequest(),
        getCajasDisponiblesRequest()
      ]);

      setClientes(clientesData);
      setOperadores(operadoresData);
      setTrailers(trailersData);
      setCajas(cajasData);
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cargar los catálogos necesarios para crear el viaje"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalogos();
  }, [loadCatalogos]);

  useEffect(() => {
    if (createdViaje) {
      return;
    }

    const operador = searchParams.get("operador");
    const trailer = searchParams.get("trailer");
    const caja = searchParams.get("caja");

    setAsignacionForm((current) => ({
      ...current,
      id_operador:
        operador && operadores.some((item) => item.id_operador === Number(operador))
          ? operador
          : current.id_operador && operadores.some((item) => item.id_operador === Number(current.id_operador))
            ? current.id_operador
            : "",
      id_trailer:
        trailer && trailers.some((item) => item.id_trailer === Number(trailer))
          ? trailer
          : current.id_trailer && trailers.some((item) => item.id_trailer === Number(current.id_trailer))
            ? current.id_trailer
            : "",
      id_caja:
        caja && cajas.some((item) => item.id_caja === Number(caja))
          ? caja
          : current.id_caja && cajas.some((item) => item.id_caja === Number(current.id_caja))
            ? current.id_caja
            : "",
    }));
  }, [cajas, createdViaje, operadores, searchParams, trailers]);

  const clientesActivos = useMemo(
    () => clientes.filter((cliente) => cliente.activo),
    [clientes]
  );

  const selectedCliente = useMemo(
    () =>
      clientesActivos.find((cliente) => cliente.id_cliente === Number(viajeForm.id_cliente)) ?? null,
    [clientesActivos, viajeForm.id_cliente]
  );

  const missingRequiredFields = useMemo(() => {
    const missing: string[] = [];

    if (!viajeForm.id_cliente) {
      missing.push("cliente");
    }

    if (!viajeForm.lugar_inicio.trim()) {
      missing.push("origen");
    }

    if (!viajeForm.lugar_destino.trim()) {
      missing.push("destino");
    }

    return missing;
  }, [
    viajeForm.id_cliente,
    viajeForm.lugar_destino,
    viajeForm.lugar_inicio,
  ]);

  function resetFlow() {
    setCreatedViaje(null);
    setViajeForm(initialViajeForm);
    setAsignacionForm(initialAsignacionForm);
    setCreateError(null);
    setAssignError(null);
  }

  async function handleCreateViaje() {
    setCreating(true);
    setCreateError(null);

    try {
      const viaje = await createViajeRequest(
        {
          folio_viaje_cliente: viajeForm.folio_viaje_cliente.trim() || null,
          id_cliente: Number(viajeForm.id_cliente),
          lugar_inicio: viajeForm.lugar_inicio.trim(),
          lugar_destino: viajeForm.lugar_destino.trim(),
          lugar_inicio_latitud: viajeForm.lugar_inicio_latitud,
          lugar_inicio_longitud: viajeForm.lugar_inicio_longitud,
          lugar_destino_latitud: viajeForm.lugar_destino_latitud,
          lugar_destino_longitud: viajeForm.lugar_destino_longitud,
          tipo_carga: viajeForm.tipo_carga.trim() || null,
          descripcion_carga: viajeForm.descripcion_carga.trim() || null,
          fecha_programada_salida: viajeForm.fecha_programada_salida || null,
          fecha_carga: viajeForm.fecha_carga || null,
          hora_carga: viajeForm.hora_carga || null,
          fecha_descarga: viajeForm.fecha_descarga || null,
          hora_descarga: viajeForm.hora_descarga || null,
          hora_cita_descarga: viajeForm.hora_descarga || null,
          observaciones: viajeForm.observaciones.trim() || null
        },
        user?.id_usuario ?? null
      );

      setCreatedViaje(viaje);
      setAssignError(null);
      await loadCatalogos();
    } catch (currentError) {
      setCreateError(
        currentError instanceof ApiError ? currentError.message : "No fue posible crear el viaje"
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleAsignar() {
    if (!createdViaje) {
      return;
    }

    setAssigning(true);
    setAssignError(null);

    try {
      await asignarViajeRequest(createdViaje.id_viaje, {
        id_operador: Number(asignacionForm.id_operador),
        id_trailer: Number(asignacionForm.id_trailer),
        id_caja: asignacionForm.id_caja ? Number(asignacionForm.id_caja) : null,
        created_by: user?.id_usuario ?? null,
        motivo: asignacionForm.motivo.trim() || null,
        comentario: asignacionForm.comentario.trim() || null
      });

      router.push(`/viajes/${createdViaje.id_viaje}`);
    } catch (currentError) {
      setAssignError(
        currentError instanceof ApiError ? currentError.message : "No fue posible asignar el viaje"
      );
    } finally {
      setAssigning(false);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando catálogo operativo..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void loadCatalogos()} />;
  }

  if (!clientesActivos.length) {
    return (
      <div className="space-y-6">
        <AdminPageHeader
          eyebrow="Administración"
          title="Nuevo viaje"
          description="Primero necesitas al menos un cliente activo para poder crear viajes desde la app."
        />
        <AdminEmptyState
          title="No hay clientes activos disponibles"
          description="Crea o activa un cliente antes de intentar dar de alta un viaje."
        />
        <div className="flex gap-3">
          <Link
            className="inline-flex items-center justify-center rounded-2xl bg-brand-700 px-4 py-3 text-sm font-medium text-white"
            href="/admin/clientes"
          >
            Ir a clientes
          </Link>
          <Link
            className="inline-flex items-center justify-center rounded-2xl bg-slate-100 px-4 py-3 text-sm font-medium text-slate-900"
            href="/viajes"
          >
            Volver a viajes
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Administración"
        title="Nuevo viaje"
        description="Crea el viaje y, si hace falta, deja la asignación para después sin romper el flujo operativo."
      />

      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <section className="rounded-[2rem] border border-brand-100 bg-white p-6 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">
                Paso 1
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                {createdViaje ? "Viaje creado" : "Captura del viaje"}
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                {createdViaje
                  ? "El viaje ya quedó registrado. Revisa el resumen y pasa al bloque de asignación."
                  : "Captura la información base que utiliza el backend para dar de alta el viaje."}
              </p>
              {!createdViaje ? (
                <div className="mt-2 space-y-1 text-sm text-brand-700">
                  <p>Puedes asignar operador, tráiler y caja después.</p>
                  {asignacionForm.id_operador || asignacionForm.id_trailer || asignacionForm.id_caja ? (
                    <p className="text-slate-600">
                      Se detectaron recursos preseleccionados desde disponibilidad. Puedes cambiarlos o quitarlos antes de asignar.
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
            {createdViaje ? (
              <Button onClick={resetFlow} type="button" variant="secondary">
                Crear otro
              </Button>
            ) : null}
          </div>

          {!createdViaje ? (
            <>
              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <Input
                  label="Folio del cliente"
                  onChange={(event) =>
                    setViajeForm((current) => ({
                      ...current,
                      folio_viaje_cliente: event.target.value
                    }))
                  }
                  placeholder="OC-45892"
                  value={viajeForm.folio_viaje_cliente}
                />
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  <p className="font-medium text-slate-900">Folio interno</p>
                  <p className="mt-1">El folio interno se generará automáticamente al guardar.</p>
                </div>
                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Cliente</span>
                  <select
                    className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                    onChange={(event) =>
                      setViajeForm((current) => ({ ...current, id_cliente: event.target.value }))
                    }
                    value={viajeForm.id_cliente}
                  >
                    <option value="">Selecciona un cliente</option>
                    {clientesActivos.map((cliente) => (
                      <option key={cliente.id_cliente} value={cliente.id_cliente}>
                        {cliente.nombre_razon_social}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="md:col-span-2">
                  <LocationPicker
                    address={viajeForm.lugar_inicio}
                    label="Ubicación de inicio"
                    latitude={viajeForm.lugar_inicio_latitud}
                    longitude={viajeForm.lugar_inicio_longitud}
                    onAddressChange={(value) =>
                      setViajeForm((current) => ({ ...current, lugar_inicio: value }))
                    }
                    onCoordinatesChange={({ latitud, longitud }) =>
                      setViajeForm((current) => ({
                        ...current,
                        lugar_inicio_latitud: latitud,
                        lugar_inicio_longitud: longitud,
                      }))
                    }
                  />
                </div>
                <div className="md:col-span-2">
                  <LocationPicker
                    address={viajeForm.lugar_destino}
                    label="Ubicación de destino"
                    latitude={viajeForm.lugar_destino_latitud}
                    longitude={viajeForm.lugar_destino_longitud}
                    onAddressChange={(value) =>
                      setViajeForm((current) => ({ ...current, lugar_destino: value }))
                    }
                    onCoordinatesChange={({ latitud, longitud }) =>
                      setViajeForm((current) => ({
                        ...current,
                        lugar_destino_latitud: latitud,
                        lugar_destino_longitud: longitud,
                      }))
                    }
                  />
                </div>
                <Input
                  label="Tipo de carga"
                  onChange={(event) =>
                    setViajeForm((current) => ({ ...current, tipo_carga: event.target.value }))
                  }
                  placeholder="Producto terminado"
                  value={viajeForm.tipo_carga}
                />
                <Input
                  label="Fecha programada de salida"
                  onChange={(event) =>
                    setViajeForm((current) => ({
                      ...current,
                      fecha_programada_salida: event.target.value
                    }))
                  }
                  type="datetime-local"
                  value={viajeForm.fecha_programada_salida}
                />
                <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-slate-900">Cita de carga</p>
                  <div className="mt-3 grid gap-4 md:grid-cols-2">
                    <Input
                      label="Fecha de carga"
                      onChange={(event) =>
                        setViajeForm((current) => ({
                          ...current,
                          fecha_carga: event.target.value
                        }))
                      }
                      type="date"
                      value={viajeForm.fecha_carga}
                    />
                    <Input
                      label="Hora de carga"
                      onChange={(event) =>
                        setViajeForm((current) => ({
                          ...current,
                          hora_carga: event.target.value
                        }))
                      }
                      type="time"
                      value={viajeForm.hora_carga}
                    />
                  </div>
                </div>
                <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-slate-900">Cita de descarga</p>
                  <div className="mt-3 grid gap-4 md:grid-cols-2">
                    <Input
                      label="Fecha de descarga"
                      onChange={(event) =>
                        setViajeForm((current) => ({
                          ...current,
                          fecha_descarga: event.target.value
                        }))
                      }
                      type="date"
                      value={viajeForm.fecha_descarga}
                    />
                    <Input
                      label="Hora de descarga"
                      onChange={(event) =>
                        setViajeForm((current) => ({
                          ...current,
                          hora_descarga: event.target.value
                        }))
                      }
                      type="time"
                      value={viajeForm.hora_descarga}
                    />
                  </div>
                </div>
                <div className="md:col-span-2">
                  <Textarea
                    label="Descripción de carga"
                    onChange={(event) =>
                      setViajeForm((current) => ({
                        ...current,
                        descripcion_carga: event.target.value
                      }))
                    }
                    placeholder="Detalle del producto o instrucciones especiales."
                    value={viajeForm.descripcion_carga}
                  />
                </div>
                <div className="md:col-span-2">
                  <Textarea
                    label="Observaciones"
                    onChange={(event) =>
                      setViajeForm((current) => ({ ...current, observaciones: event.target.value }))
                    }
                    placeholder="Notas operativas para el viaje."
                    value={viajeForm.observaciones}
                  />
                </div>
              </div>

              {createError ? (
                <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {createError}
                </div>
              ) : null}

              {missingRequiredFields.length > 0 ? (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Completa: {missingRequiredFields.join(", ")}.
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                  Listo para guardar. El folio interno se generará automáticamente. La asignación, el mapa y las fechas de carga/descarga pueden capturarse después.
                </div>
              )}

              <div className="mt-6 flex flex-wrap gap-3">
                <Button
                  disabled={
                    creating ||
                    missingRequiredFields.length > 0
                  }
                  onClick={() => void handleCreateViaje()}
                  type="button"
                >
                  {creating ? "Creando viaje..." : "Guardar y continuar"}
                </Button>
                <Link
                  className="inline-flex items-center justify-center rounded-2xl bg-slate-100 px-4 py-3 text-sm font-medium text-slate-900"
                  href="/viajes"
                >
                  Cancelar
                </Link>
              </div>
            </>
          ) : (
            <div className="mt-6 space-y-4">
              <div className="rounded-[1.5rem] border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-sky-50 p-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">
                      Viaje listo para asignar
                    </p>
                    <h3 className="mt-2 text-2xl font-semibold text-slate-950">
                      {createdViaje.folio}
                    </h3>
                    <p className="mt-2 text-sm text-slate-600">
                      {selectedCliente?.nombre_razon_social ?? "Cliente seleccionado"}
                    </p>
                  </div>
                  <span className="rounded-full bg-brand-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white">
                    Creado
                  </span>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl bg-white/80 px-4 py-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Ruta
                    </p>
                    <p className="mt-2 text-sm font-medium text-slate-900">
                      {createdViaje.lugar_inicio}
                    </p>
                    <p className="text-xs text-slate-500">→</p>
                    <p className="text-sm font-medium text-slate-900">
                      {createdViaje.lugar_destino}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-white/80 px-4 py-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Carga
                    </p>
                    <p className="mt-2 text-sm text-slate-700">
                      {createdViaje.tipo_carga ?? "Sin tipo de carga"}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      Folio cliente: {createdViaje.folio_viaje_cliente ?? "Sin dato"}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      Carga: {createdViaje.fecha_carga ?? "Sin fecha"} {createdViaje.hora_carga ?? "Sin hora"}
                    </p>
                    <p className="text-sm text-slate-600">
                      Descarga: {createdViaje.fecha_descarga ?? "Sin fecha"} {createdViaje.hora_descarga ?? "Sin hora"}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {createdViaje.descripcion_carga ?? "Sin descripción registrada"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link
                  className="inline-flex items-center justify-center rounded-2xl bg-slate-100 px-4 py-3 text-sm font-medium text-slate-900"
                  href={`/viajes/${createdViaje.id_viaje}`}
                >
                  Ver detalle sin asignar
                </Link>
                <Link
                  className="inline-flex items-center justify-center rounded-2xl bg-brand-700 px-4 py-3 text-sm font-medium text-white"
                  href={`/admin/viajes/${createdViaje.id_viaje}/editar`}
                >
                  Editar o asignar después
                </Link>
              </div>
            </div>
          )}
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">Paso 2</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Asignación operativa</h2>
            <p className="mt-2 text-sm text-slate-600">
              Selecciona los recursos actuales del viaje y registra el motivo de la asignación si quieres hacerlo ahora.
            </p>
          </div>

          {!createdViaje ? (
            <div className="mt-6">
              <AdminEmptyState
                title="Primero crea el viaje"
                description="Cuando el viaje quede registrado, aquí podrás asignar operador, tráiler y caja."
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
                      setAsignacionForm((current) => ({ ...current, id_operador: event.target.value }))
                    }
                    value={asignacionForm.id_operador}
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
                      setAsignacionForm((current) => ({ ...current, id_trailer: event.target.value }))
                    }
                    value={asignacionForm.id_trailer}
                  >
                    <option value="">Selecciona un tráiler disponible</option>
                    {trailers.map((trailer) => (
                      <option key={trailer.id_trailer} value={trailer.id_trailer}>
                        {trailer.numero_economico} · {trailer.placas}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Caja</span>
                  <select
                    className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                    onChange={(event) =>
                      setAsignacionForm((current) => ({ ...current, id_caja: event.target.value }))
                    }
                    value={asignacionForm.id_caja}
                  >
                    <option value="">Sin caja</option>
                    {cajas.map((caja) => (
                      <option key={caja.id_caja} value={caja.id_caja}>
                        {(caja.numero_economico ?? "Caja sin número")} · {caja.placas}
                      </option>
                    ))}
                  </select>
                </label>

                <Input
                  label="Motivo"
                  onChange={(event) =>
                    setAsignacionForm((current) => ({ ...current, motivo: event.target.value }))
                  }
                  placeholder="Asignación inicial"
                  value={asignacionForm.motivo}
                />

                <Textarea
                  label="Comentario"
                  onChange={(event) =>
                    setAsignacionForm((current) => ({ ...current, comentario: event.target.value }))
                  }
                  placeholder="Notas internas sobre la asignación."
                  value={asignacionForm.comentario}
                />
              </div>

              {!operadores.length || !trailers.length ? (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  Se necesita al menos un operador y un tráiler disponibles para completar la asignación.
                </div>
              ) : null}

              {assignError ? (
                <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {assignError}
                </div>
              ) : null}

              <div className="mt-6 flex flex-wrap gap-3">
                <Button
                  disabled={
                    assigning ||
                    !asignacionForm.id_operador ||
                    !asignacionForm.id_trailer ||
                    !operadores.length ||
                    !trailers.length
                  }
                  onClick={() => void handleAsignar()}
                  type="button"
                >
                  {assigning ? "Asignando..." : "Asignar y abrir detalle"}
                </Button>
                <Button onClick={() => void loadCatalogos()} type="button" variant="secondary">
                  Recargar disponibilidad
                </Button>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
