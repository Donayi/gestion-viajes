"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminEmptyState } from "@/components/admin/admin-empty-state";
import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AdminTableShell } from "@/components/admin/admin-table-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { cn } from "@/lib/cn";
import { ApiError } from "@/services/api-client";
import { getDisponibilidadResumenRequest, getViajesEnrichedRequest } from "@/services/viajes.service";
import type {
  CajaDisponibilidad,
  DisponibilidadResumen,
  OperadorDisponibilidad,
  TrailerDisponibilidad,
  ViajeListItem,
} from "@/types/viaje";

type AvailabilityFilter = "todos" | "disponibles" | "no_disponibles" | "inactivos";
type AvailabilityTab = "operadores" | "trailers" | "cajas";

const tabOptions: Array<{ key: AvailabilityTab; label: string }> = [
  { key: "operadores", label: "Choferes disponibles" },
  { key: "trailers", label: "Tráilers disponibles" },
  { key: "cajas", label: "Cajas disponibles" },
];

const filterOptions: Array<{ key: AvailabilityFilter; label: string }> = [
  { key: "todos", label: "Todos" },
  { key: "disponibles", label: "Disponibles" },
  { key: "no_disponibles", label: "No disponibles" },
  { key: "inactivos", label: "Inactivos" },
];

function getAvailabilityStatus(item: { activo: boolean; disponible: boolean }) {
  if (!item.activo) {
    return {
      label: "Inactivo",
      className: "border-slate-200 bg-slate-100 text-slate-600",
    };
  }

  if (item.disponible) {
    return {
      label: "Disponible",
      className: "border-emerald-200 bg-emerald-50 text-emerald-700",
    };
  }

  return {
    label: "No disponible",
    className: "border-amber-200 bg-amber-50 text-amber-700",
  };
}

function matchesAvailabilityFilter(
  item: { activo: boolean; disponible: boolean },
  filter: AvailabilityFilter
) {
  if (filter === "todos") {
    return true;
  }

  if (filter === "disponibles") {
    return item.activo && item.disponible;
  }

  if (filter === "no_disponibles") {
    return item.activo && !item.disponible;
  }

  return !item.activo;
}

function normalize(text: string | null | undefined) {
  return (text ?? "").toLowerCase();
}

function formatViajeActual(
  viajeActual: { folio: string; estatus_clave: string | null } | null | undefined
) {
  if (!viajeActual) {
    return "Sin viaje actual";
  }

  return viajeActual.estatus_clave
    ? `${viajeActual.folio} · ${viajeActual.estatus_clave}`
    : viajeActual.folio;
}

function buildQuickCreateHref(params: { operador?: number; trailer?: number; caja?: number }) {
  const search = new URLSearchParams();

  if (params.operador) {
    search.set("operador", String(params.operador));
  }
  if (params.trailer) {
    search.set("trailer", String(params.trailer));
  }
  if (params.caja) {
    search.set("caja", String(params.caja));
  }

  const query = search.toString();
  return query ? `/admin/viajes/nuevo?${query}` : "/admin/viajes/nuevo";
}

function filterOperadores(
  operadores: OperadorDisponibilidad[],
  filter: AvailabilityFilter,
  search: string
) {
  const query = search.trim().toLowerCase();
  return operadores.filter((operador) => {
    if (!matchesAvailabilityFilter(operador, filter)) {
      return false;
    }

    if (!query) {
      return true;
    }

    const searchable = [
      operador.alias,
      operador.username,
      operador.nombre_completo,
      operador.numero_licencia,
      operador.motivo_no_disponible,
      operador.viaje_actual?.folio,
    ]
      .map(normalize)
      .join(" ");

    return searchable.includes(query);
  });
}

function filterTrailers(
  trailers: TrailerDisponibilidad[],
  filter: AvailabilityFilter,
  search: string
) {
  const query = search.trim().toLowerCase();
  return trailers.filter((trailer) => {
    if (!matchesAvailabilityFilter(trailer, filter)) {
      return false;
    }

    if (!query) {
      return true;
    }

    const searchable = [
      trailer.numero_economico,
      trailer.placas,
      trailer.marca,
      trailer.modelo,
      trailer.numero_serie,
      trailer.motivo_no_disponible,
      trailer.viaje_actual?.folio,
    ]
      .map(normalize)
      .join(" ");

    return searchable.includes(query);
  });
}

function filterCajas(cajas: CajaDisponibilidad[], filter: AvailabilityFilter, search: string) {
  const query = search.trim().toLowerCase();
  return cajas.filter((caja) => {
    if (!matchesAvailabilityFilter(caja, filter)) {
      return false;
    }

    if (!query) {
      return true;
    }

    const searchable = [
      caja.numero_economico,
      caja.placas,
      caja.tipo_caja,
      caja.modelo,
      caja.numero_serie,
      caja.motivo_no_disponible,
      caja.viaje_actual?.folio,
    ]
      .map(normalize)
      .join(" ");

    return searchable.includes(query);
  });
}

function isViajePendienteAsignacion(viaje: ViajeListItem) {
  return (
    viaje.estatus_actual.clave === "CREADO" ||
    viaje.id_operador_actual === null ||
    viaje.id_trailer_actual === null
  );
}

function filterViajesPendientes(viajes: ViajeListItem[], search: string) {
  const query = search.trim().toLowerCase();

  return viajes.filter((viaje) => {
    if (!isViajePendienteAsignacion(viaje)) {
      return false;
    }

    if (!query) {
      return true;
    }

    const searchable = [
      viaje.folio,
      viaje.folio_viaje_cliente,
      viaje.cliente.nombre_razon_social,
      viaje.lugar_inicio,
      viaje.lugar_destino,
      viaje.estatus_actual.clave,
      viaje.operador_actual?.alias,
      viaje.trailer_actual?.numero_economico,
      viaje.caja_actual?.numero_economico,
      viaje.caja_actual?.placas,
    ]
      .map(normalize)
      .join(" ");

    return searchable.includes(query);
  });
}

export default function AdminDisponibilidadPage() {
  const [summary, setSummary] = useState<DisponibilidadResumen | null>(null);
  const [viajes, setViajes] = useState<ViajeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<AvailabilityTab>("operadores");
  const [activeFilter, setActiveFilter] = useState<AvailabilityFilter>("todos");
  const [search, setSearch] = useState("");
  const [pendingSearch, setPendingSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, viajesData] = await Promise.all([
        getDisponibilidadResumenRequest(),
        getViajesEnrichedRequest(),
      ]);
      setSummary(summaryData);
      setViajes(viajesData);
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cargar el resumen de disponibilidad"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const operadores = useMemo(
    () => filterOperadores(summary?.operadores ?? [], activeFilter, search),
    [activeFilter, search, summary?.operadores]
  );
  const trailers = useMemo(
    () => filterTrailers(summary?.trailers ?? [], activeFilter, search),
    [activeFilter, search, summary?.trailers]
  );
  const cajas = useMemo(
    () => filterCajas(summary?.cajas ?? [], activeFilter, search),
    [activeFilter, search, summary?.cajas]
  );
  const viajesPendientes = useMemo(
    () => filterViajesPendientes(viajes, pendingSearch),
    [pendingSearch, viajes]
  );

  if (loading) {
    return <LoadingState label="Cargando disponibilidad operativa..." />;
  }

  if (error || !summary) {
    return (
      <ErrorState
        message={error ?? "No fue posible cargar la disponibilidad operativa"}
        onRetry={() => void load()}
      />
    );
  }

  const counters = [
    {
      title: "Choferes disponibles",
      available: summary.operadores.filter((item) => item.activo && item.disponible).length,
      totalActive: summary.operadores.filter((item) => item.activo).length,
    },
    {
      title: "Tráilers disponibles",
      available: summary.trailers.filter((item) => item.activo && item.disponible).length,
      totalActive: summary.trailers.filter((item) => item.activo).length,
    },
    {
      title: "Cajas disponibles",
      available: summary.cajas.filter((item) => item.activo && item.disponible).length,
      totalActive: summary.cajas.filter((item) => item.activo).length,
    },
  ];

  const currentRowsCount =
    activeTab === "operadores" ? operadores.length : activeTab === "trailers" ? trailers.length : cajas.length;

  return (
    <div className="space-y-6">
      <AdminPageHeader
        description="Consulta recursos activos, ocupados o inactivos para decidir asignaciones y movimientos operativos."
        eyebrow="Planeación"
        title="Disponibilidad operativa"
      />

      <section className="grid gap-4 xl:grid-cols-3">
        {counters.map((counter) => (
          <Card key={counter.title} className="border-brand-100 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              {counter.title}
            </p>
            <div className="mt-4 flex items-end gap-2">
              <span className="text-3xl font-semibold text-slate-950">{counter.available}</span>
              <span className="pb-1 text-sm text-slate-500">de {counter.totalActive} activos</span>
            </div>
            <p className="mt-3 text-sm text-slate-600">
              {counter.available === counter.totalActive
                ? "Sin bloqueos operativos en este momento."
                : "Revisa no disponibles e inactivos para planear la siguiente asignación."}
            </p>
          </Card>
        ))}
      </section>

      <AdminTableShell
        action={
          <div className="w-full max-w-md">
            <Input
              label="Buscar viaje pendiente"
              onChange={(event) => setPendingSearch(event.target.value)}
              placeholder="Folio, cliente, origen, destino..."
              value={pendingSearch}
            />
          </div>
        }
        title={`Viajes pendientes por asignar (${viajesPendientes.length})`}
      >
        {viajesPendientes.length === 0 ? (
          <div className="p-5">
            <AdminEmptyState
              description="No hay viajes creados pendientes de asignación en este momento."
              title="No hay viajes pendientes por asignar"
            />
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {[
                  "Folio",
                  "Cliente",
                  "Ruta",
                  "Fecha salida",
                  "Folio cliente",
                  "Estado",
                  "Recursos actuales",
                  "Acción",
                ].map((header) => (
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
              {viajesPendientes.map((viaje) => (
                <tr key={viaje.id_viaje} className="border-t border-slate-100">
                  <td className="px-4 py-4 font-semibold text-slate-950">{viaje.folio}</td>
                  <td className="px-4 py-4 text-slate-700">{viaje.cliente.nombre_razon_social}</td>
                  <td className="px-4 py-4 text-slate-700">
                    <div>{viaje.lugar_inicio}</div>
                    <div className="text-xs text-slate-500">→ {viaje.lugar_destino}</div>
                  </td>
                  <td className="px-4 py-4 text-slate-700">
                    {viaje.fecha_programada_salida
                      ? new Date(viaje.fecha_programada_salida).toLocaleString("es-MX")
                      : "Sin dato"}
                  </td>
                  <td className="px-4 py-4 text-slate-700">{viaje.folio_viaje_cliente ?? "Sin dato"}</td>
                  <td className="px-4 py-4">
                    <span className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">
                      {viaje.estatus_actual.clave}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-slate-700">
                    <div>Operador: {viaje.operador_actual?.alias ?? "Sin asignar"}</div>
                    <div>Tráiler: {viaje.trailer_actual?.numero_economico ?? "Sin asignar"}</div>
                    <div>
                      Caja: {viaje.caja_actual?.numero_economico ?? viaje.caja_actual?.placas ?? "Sin asignar"}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <Link href={`/admin/viajes/${viaje.id_viaje}/editar`}>
                      <Button type="button" variant="secondary">
                        Asignar recursos
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </AdminTableShell>

      <Card className="border-brand-100 p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {tabOptions.map((tab) => (
                <Button
                  key={tab.key}
                  className={cn(
                    activeTab === tab.key && "ring-2 ring-brand-200"
                  )}
                  onClick={() => setActiveTab(tab.key)}
                  type="button"
                  variant={activeTab === tab.key ? "primary" : "secondary"}
                >
                  {tab.label}
                </Button>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              {filterOptions.map((filter) => (
                <Button
                  key={filter.key}
                  onClick={() => setActiveFilter(filter.key)}
                  type="button"
                  variant={activeFilter === filter.key ? "primary" : "ghost"}
                >
                  {filter.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="w-full xl:max-w-md">
            <Input
              label="Buscar recurso"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Alias, placas, número económico, folio..."
              value={search}
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <Link href="/admin/viajes/nuevo" title="Crear viaje sin preselección de recursos">
            <Button type="button">Crear viaje rápido</Button>
          </Link>
        </div>
      </Card>

      {activeTab === "operadores" ? (
        operadores.length === 0 ? (
          <AdminEmptyState
            description="Ajusta el filtro o la búsqueda para encontrar recursos en esta vista."
            title="No hay operadores para mostrar"
          />
        ) : (
          <AdminTableShell title={`Choferes disponibles actuales (${currentRowsCount})`}>
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Alias", "Usuario", "Licencia", "Estado", "Viaje actual", "Motivo", "Acción"].map((header) => (
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
                {operadores.map((operador) => {
                  const status = getAvailabilityStatus(operador);
                  return (
                    <tr key={operador.id_operador} className="border-t border-slate-100">
                      <td className="px-4 py-4 font-semibold text-slate-950">{operador.alias}</td>
                      <td className="px-4 py-4 text-slate-700">
                        <div>{operador.username ?? "Sin usuario"}</div>
                        <div className="text-xs text-slate-500">{operador.nombre_completo ?? "Sin nombre"}</div>
                      </td>
                      <td className="px-4 py-4 text-slate-700">{operador.numero_licencia ?? "Sin dato"}</td>
                      <td className="px-4 py-4">
                        <span
                          className={cn(
                            "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                            status.className
                          )}
                        >
                          {status.label}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-700">{formatViajeActual(operador.viaje_actual)}</td>
                      <td className="px-4 py-4 text-slate-700">{operador.motivo_no_disponible ?? "Disponible"}</td>
                      <td className="px-4 py-4">
                        {operador.disponible ? (
                          <Link
                            href={buildQuickCreateHref({ operador: operador.id_operador })}
                            title="Crear viaje con este recurso preseleccionado"
                          >
                            <Button type="button" variant="secondary">
                              Asignar a viaje
                            </Button>
                          </Link>
                        ) : (
                          <span className="text-sm text-slate-400">No disponible</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </AdminTableShell>
        )
      ) : null}

      {activeTab === "trailers" ? (
        trailers.length === 0 ? (
          <AdminEmptyState
            description="Ajusta el filtro o la búsqueda para encontrar recursos en esta vista."
            title="No hay tráilers para mostrar"
          />
        ) : (
          <AdminTableShell title={`Tráilers disponibles actuales (${currentRowsCount})`}>
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Número económico", "Placas", "Marca / modelo", "Serie", "Estado", "Viaje actual", "Motivo", "Acción"].map(
                    (header) => (
                      <th
                        key={header}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                      >
                        {header}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {trailers.map((trailer) => {
                  const status = getAvailabilityStatus(trailer);
                  return (
                    <tr key={trailer.id_trailer} className="border-t border-slate-100">
                      <td className="px-4 py-4 font-semibold text-slate-950">{trailer.numero_economico}</td>
                      <td className="px-4 py-4 text-slate-700">{trailer.placas}</td>
                      <td className="px-4 py-4 text-slate-700">
                        {[trailer.marca, trailer.modelo].filter(Boolean).join(" / ") || "Sin dato"}
                      </td>
                      <td className="px-4 py-4 text-slate-700">{trailer.numero_serie ?? "Sin dato"}</td>
                      <td className="px-4 py-4">
                        <span
                          className={cn(
                            "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                            status.className
                          )}
                        >
                          {status.label}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-700">{formatViajeActual(trailer.viaje_actual)}</td>
                      <td className="px-4 py-4 text-slate-700">{trailer.motivo_no_disponible ?? "Disponible"}</td>
                      <td className="px-4 py-4">
                        {trailer.disponible ? (
                          <Link
                            href={buildQuickCreateHref({ trailer: trailer.id_trailer })}
                            title="Crear viaje con este recurso preseleccionado"
                          >
                            <Button type="button" variant="secondary">
                              Asignar a viaje
                            </Button>
                          </Link>
                        ) : (
                          <span className="text-sm text-slate-400">No disponible</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </AdminTableShell>
        )
      ) : null}

      {activeTab === "cajas" ? (
        cajas.length === 0 ? (
          <AdminEmptyState
            description="Ajusta el filtro o la búsqueda para encontrar recursos en esta vista."
            title="No hay cajas para mostrar"
          />
        ) : (
          <AdminTableShell title={`Cajas disponibles actuales (${currentRowsCount})`}>
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Número económico", "Placas", "Tipo", "Tamaño", "Serie", "Estado", "Viaje actual", "Motivo", "Acción"].map(
                    (header) => (
                      <th
                        key={header}
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                      >
                        {header}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {cajas.map((caja) => {
                  const status = getAvailabilityStatus(caja);
                  return (
                    <tr key={caja.id_caja} className="border-t border-slate-100">
                      <td className="px-4 py-4 font-semibold text-slate-950">{caja.numero_economico ?? "Sin dato"}</td>
                      <td className="px-4 py-4 text-slate-700">{caja.placas}</td>
                      <td className="px-4 py-4 text-slate-700">{caja.tipo_caja ?? "Sin dato"}</td>
                      <td className="px-4 py-4 text-slate-700">{caja.modelo ?? "Sin dato"}</td>
                      <td className="px-4 py-4 text-slate-700">{caja.numero_serie ?? "Sin dato"}</td>
                      <td className="px-4 py-4">
                        <span
                          className={cn(
                            "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
                            status.className
                          )}
                        >
                          {status.label}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-700">{formatViajeActual(caja.viaje_actual)}</td>
                      <td className="px-4 py-4 text-slate-700">{caja.motivo_no_disponible ?? "Disponible"}</td>
                      <td className="px-4 py-4">
                        {caja.disponible ? (
                          <Link
                            href={buildQuickCreateHref({ caja: caja.id_caja })}
                            title="Crear viaje con este recurso preseleccionado"
                          >
                            <Button type="button" variant="secondary">
                              Asignar a viaje
                            </Button>
                          </Link>
                        ) : (
                          <span className="text-sm text-slate-400">No disponible</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </AdminTableShell>
        )
      ) : null}
    </div>
  );
}
