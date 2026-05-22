"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/status-badge";
import { ViajeOperativoMap } from "@/components/viajes/viaje-operativo-map";
import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import { getViajesMapaRequest } from "@/services/viajes.service";
import { ApiError } from "@/services/api-client";
import type { ViajeMapaItem } from "@/types/viaje";

const statusOptions = [
  { clave: "CREADO", nombre: "Creado", badge: "neutral" as const },
  { clave: "ASIGNADO", nombre: "Asignado", badge: "info" as const },
  { clave: "CARGANDO", nombre: "Cargando", badge: "primary" as const },
  { clave: "INICIADO", nombre: "Iniciado", badge: "success" as const },
  { clave: "RETRASADO", nombre: "Retrasado", badge: "warning" as const },
  { clave: "STANDBY", nombre: "Standby", badge: "warning" as const },
  { clave: "FINALIZADO", nombre: "Finalizado", badge: "success" as const },
  { clave: "CANCELADO", nombre: "Cancelado", badge: "danger" as const },
];

function hasLocation(viaje: ViajeMapaItem) {
  return (
    viaje.ultima_ubicacion !== null &&
    viaje.ultima_ubicacion.latitud !== null &&
    viaje.ultima_ubicacion.longitud !== null
  );
}

export default function AdminMapaViajesPage() {
  const [viajes, setViajes] = useState<ViajeMapaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(statusOptions.map((status) => status.clave));
  const [showFinalizados, setShowFinalizados] = useState(true);
  const [showCancelados, setShowCancelados] = useState(false);

  const deferredSearch = useDeferredValue(search);

  useEffect(() => {
    async function loadMap() {
      if (selectedStatuses.length === 0) {
        setViajes([]);
        setLoading(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const data = await getViajesMapaRequest({
          estatus: selectedStatuses,
          incluirFinalizados: showFinalizados,
          incluirCancelados: showCancelados,
        });
        setViajes(data);
      } catch (currentError) {
        setError(
          currentError instanceof ApiError
            ? currentError.message
            : "No fue posible cargar el mapa operativo de viajes."
        );
      } finally {
        setLoading(false);
      }
    }

    void loadMap();
  }, [selectedStatuses, showCancelados, showFinalizados]);

  const filteredViajes = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase();
    if (!normalizedSearch) {
      return viajes;
    }

    return viajes.filter((viaje) => {
      const haystack = [
        viaje.folio,
        viaje.folio_viaje_cliente,
        viaje.cliente.nombre_razon_social,
        viaje.operador_actual?.alias,
        viaje.trailer_actual?.numero_economico,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalizedSearch);
    });
  }, [deferredSearch, viajes]);

  const viajesSinUbicacion = useMemo(
    () => filteredViajes.filter((viaje) => !hasLocation(viaje)),
    [filteredViajes]
  );

  const statusCounts = useMemo(() => {
    return filteredViajes.reduce<Record<string, number>>((accumulator, viaje) => {
      accumulator[viaje.estatus_actual.clave] = (accumulator[viaje.estatus_actual.clave] ?? 0) + 1;
      return accumulator;
    }, {});
  }, [filteredViajes]);

  function toggleStatus(clave: string) {
    setSelectedStatuses((current) =>
      current.includes(clave) ? current.filter((item) => item !== clave) : [...current, clave]
    );
  }

  if (loading) {
    return <LoadingState label="Cargando mapa operativo de viajes..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">Visibilidad operativa</p>
        <h1 className="text-3xl font-semibold text-slate-950">Mapa de viajes</h1>
        <p className="text-sm text-slate-600">
          Visualiza la última ubicación conocida de cada viaje y filtra por estatus, folio o recurso actual.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-5">
          <p className="text-sm text-slate-500">Viajes mostrados</p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{filteredViajes.length}</p>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-slate-500">Con ubicación</p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{filteredViajes.length - viajesSinUbicacion.length}</p>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-slate-500">Sin ubicación</p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{viajesSinUbicacion.length}</p>
        </Card>
      </div>

      <Card className="p-5 md:p-6">
        <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <Input
              label="Buscar por folio, cliente u operador"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Ej. F-001, Acme, Juan"
              value={search}
            />

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Estatus visibles</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {statusOptions.map((status) => {
                  const active = selectedStatuses.includes(status.clave);
                  return (
                    <button
                      className={`rounded-full border px-3 py-2 text-sm font-medium transition ${
                        active
                          ? "border-brand-200 bg-brand-50 text-brand-800"
                          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                      key={status.clave}
                      onClick={() => toggleStatus(status.clave)}
                      type="button"
                    >
                      {status.nombre}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Toggles</p>
              <div className="mt-3 space-y-3">
                <label className="flex items-center gap-3 text-sm text-slate-700">
                  <input
                    checked={showFinalizados}
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    onChange={(event) => setShowFinalizados(event.target.checked)}
                    type="checkbox"
                  />
                  <span>Mostrar finalizados</span>
                </label>
                <label className="flex items-center gap-3 text-sm text-slate-700">
                  <input
                    checked={showCancelados}
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    onChange={(event) => setShowCancelados(event.target.checked)}
                    type="checkbox"
                  />
                  <span>Mostrar cancelados</span>
                </label>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Conteo por estatus</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {statusOptions.map((status) => (
                  <StatusBadge className="gap-2" key={status.clave} variant={status.badge}>
                    {status.nombre} · {statusCounts[status.clave] ?? 0}
                  </StatusBadge>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <ViajeOperativoMap viajes={filteredViajes.filter((viaje) => hasLocation(viaje))} />

      {viajesSinUbicacion.length > 0 ? (
        <Card className="p-5 md:p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">Seguimiento pendiente</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950">Viajes sin ubicación</h2>
            </div>
            <StatusBadge variant="inactive">{viajesSinUbicacion.length}</StatusBadge>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {viajesSinUbicacion.map((viaje) => (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4" key={viaje.id_viaje}>
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold text-slate-950">{viaje.folio}</p>
                  <ViajeStatusBadge clave={viaje.estatus_actual.clave} nombre={viaje.estatus_actual.nombre} />
                </div>
                <p className="mt-2 text-sm text-slate-700">{viaje.cliente.nombre_razon_social}</p>
                <p className="mt-2 text-xs text-slate-500">Origen: {viaje.lugar_inicio}</p>
                <p className="mt-1 text-xs text-slate-500">Destino: {viaje.lugar_destino}</p>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
