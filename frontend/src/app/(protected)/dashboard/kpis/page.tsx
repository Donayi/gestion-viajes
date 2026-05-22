"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { KpiEmptyState } from "@/components/kpis/kpi-empty-state";
import { KpiSummaryCards } from "@/components/kpis/kpi-summary-cards";
import { KpiTripTable } from "@/components/kpis/kpi-trip-table";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { StatusBadge } from "@/components/ui/status-badge";
import { useSession } from "@/hooks/use-session";
import { isAdmin } from "@/lib/permissions";
import { ApiError } from "@/services/api-client";
import { getClientesRequest } from "@/services/clientes.service";
import {
  getKpisClientesRequest,
  getKpisOperadoresRequest,
  getKpisOperativosRequest,
  getKpisTrailersRequest,
} from "@/services/kpis.service";
import { getOperadoresRequest } from "@/services/operadores.service";
import { getTrailersRequest } from "@/services/trailers.service";
import type { Cliente } from "@/types/cliente";
import type {
  KpiCatalogFilters,
  KpiClientesResponse,
  KpiOperadoresResponse,
  KpiOperativoDashboard,
  KpiOperativoFilters,
  KpiTrailersResponse,
} from "@/types/kpi";
import type { Operador } from "@/types/operador";
import type { Trailer } from "@/types/trailer";

type TabKey = "operadores" | "trailers" | "clientes" | "operativo";
type LookupOption = {
  id: number;
  label: string;
  description?: string | null;
};

const tabs: { key: TabKey; label: string }[] = [
  { key: "operadores", label: "Operadores" },
  { key: "trailers", label: "Tráilers" },
  { key: "clientes", label: "Clientes" },
  { key: "operativo", label: "Operativo" },
];

const initialCatalogFilters: KpiCatalogFilters = {};
const initialOperativoFilters: KpiOperativoFilters = { solo_completos: false };

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "Sin dato";
  return value.toLocaleString("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function findLookupMatch(value: string, options: LookupOption[]) {
  const normalized = value.trim().toLocaleLowerCase();
  if (!normalized) {
    return null;
  }

  return (
    options.find((option) => option.label.trim().toLocaleLowerCase() === normalized) ?? null
  );
}

function BasicSummaryCards({
  items,
}: {
  items: Array<{ label: string; value: number | null }>;
}) {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <Card
          key={item.label}
          className="border-brand-100 bg-gradient-to-br from-brand-50 via-white to-slate-50 p-5"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
            {item.label}
          </p>
          <p className="mt-4 text-3xl font-semibold text-slate-950">{formatNumber(item.value)}</p>
        </Card>
      ))}
    </section>
  );
}

function SeriesCard({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: Array<{ etiqueta: string; valor: number }>;
}) {
  return (
    <Card className="p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">{title}</p>
      <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
      {items.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">Sin datos para la serie seleccionada.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <div className="flex items-center justify-between gap-3 text-sm" key={item.etiqueta}>
              <span className="text-slate-600">{item.etiqueta}</span>
              <StatusBadge variant="info">{formatNumber(item.valor)}</StatusBadge>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function KpisDashboardPage() {
  const { user } = useSession();
  const admin = isAdmin(user);
  const [activeTab, setActiveTab] = useState<TabKey>("operadores");
  const [catalogFilters, setCatalogFilters] = useState<KpiCatalogFilters>(initialCatalogFilters);
  const [appliedCatalogFilters, setAppliedCatalogFilters] =
    useState<KpiCatalogFilters>(initialCatalogFilters);
  const [operativoFilters, setOperativoFilters] =
    useState<KpiOperativoFilters>(initialOperativoFilters);
  const [appliedOperativoFilters, setAppliedOperativoFilters] =
    useState<KpiOperativoFilters>(initialOperativoFilters);
  const [operadoresData, setOperadoresData] = useState<KpiOperadoresResponse | null>(null);
  const [trailersData, setTrailersData] = useState<KpiTrailersResponse | null>(null);
  const [clientesData, setClientesData] = useState<KpiClientesResponse | null>(null);
  const [operativoData, setOperativoData] = useState<KpiOperativoDashboard | null>(null);
  const [operadoresOptions, setOperadoresOptions] = useState<LookupOption[]>([]);
  const [trailersOptions, setTrailersOptions] = useState<LookupOption[]>([]);
  const [clientesOptions, setClientesOptions] = useState<LookupOption[]>([]);
  const [operatorSearch, setOperatorSearch] = useState("");
  const [trailerSearch, setTrailerSearch] = useState("");
  const [clientSearch, setClientSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLookups = useCallback(async () => {
    const [operadores, trailers, clientes] = await Promise.all([
      getOperadoresRequest(),
      getTrailersRequest(),
      getClientesRequest(),
    ]);

    setOperadoresOptions(
      operadores.map((operador: Operador) => ({
        id: operador.id_operador,
        label: operador.alias,
        description: operador.numero_licencia,
      }))
    );
    setTrailersOptions(
      trailers.map((trailer: Trailer) => ({
        id: trailer.id_trailer,
        label: trailer.numero_economico,
        description: trailer.placas,
      }))
    );
    setClientesOptions(
      clientes.map((cliente: Cliente) => ({
        id: cliente.id_cliente,
        label: cliente.nombre_razon_social,
        description: cliente.rfc,
      }))
    );
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (activeTab === "operadores") {
        setOperadoresData(await getKpisOperadoresRequest(appliedCatalogFilters));
      } else if (activeTab === "trailers") {
        setTrailersData(await getKpisTrailersRequest(appliedCatalogFilters));
      } else if (activeTab === "clientes") {
        setClientesData(await getKpisClientesRequest(appliedCatalogFilters));
      } else {
        setOperativoData(await getKpisOperativosRequest(appliedOperativoFilters));
      }
    } catch (currentError) {
      setError(
        currentError instanceof ApiError ? currentError.message : "No fue posible cargar los KPIs"
      );
    } finally {
      setLoading(false);
    }
  }, [activeTab, appliedCatalogFilters, appliedOperativoFilters]);

  useEffect(() => {
    void loadLookups();
  }, [loadLookups]);

  useEffect(() => {
    void load();
  }, [load]);

  const activeDataEmpty = useMemo(() => {
    if (activeTab === "operadores") return (operadoresData?.operadores.length ?? 0) === 0;
    if (activeTab === "trailers") return (trailersData?.trailers.length ?? 0) === 0;
    if (activeTab === "clientes") return (clientesData?.clientes.length ?? 0) === 0;
    return (operativoData?.viajes.length ?? 0) === 0;
  }, [activeTab, clientesData, operativoData, operadoresData, trailersData]);

  const emptyMessage = useMemo(() => {
    if (activeTab === "operadores") {
      return operatorSearch
        ? "No hay viajes registrados para este operador."
        : "No hay viajes registrados para los operadores seleccionados.";
    }
    if (activeTab === "trailers") {
      return trailerSearch
        ? "No hay rendimiento calculable para este tráiler."
        : "No hay rendimiento calculable para los tráilers seleccionados.";
    }
    if (activeTab === "clientes") {
      return clientSearch
        ? "No hay viajes registrados para este cliente."
        : "No hay viajes registrados para los clientes seleccionados.";
    }
    return "No hay datos operativos para los filtros seleccionados.";
  }, [activeTab, clientSearch, operatorSearch, trailerSearch]);

  if (loading) {
    return <LoadingState label="Cargando KPIs..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-r from-brand-800 via-brand-700 to-slate-900 px-6 py-7 text-white shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/70">
          Dashboard ejecutivo
        </p>
        <div className="mt-3">
          <h1 className="text-3xl font-semibold">KPIs operativos catalogados</h1>
          <p className="mt-2 max-w-3xl text-sm text-white/80">
            {admin
              ? "Consulta indicadores reales por operador, tráiler y cliente, además del tablero operativo actual."
              : "Consulta indicadores operativos disponibles para tu perfil."}
          </p>
        </div>
      </section>

      <Card className="p-5">
        <div className="flex flex-wrap gap-3">
          {tabs.map((tab) => (
            <Button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              type="button"
              variant={activeTab === tab.key ? "primary" : "outline"}
            >
              {tab.label}
            </Button>
          ))}
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Input
            label="Fecha inicio"
            onChange={(event) => {
              setCatalogFilters((current) => ({
                ...current,
                fecha_inicio: event.target.value || undefined,
              }));
              setOperativoFilters((current) => ({
                ...current,
                fecha_desde: event.target.value || undefined,
              }));
            }}
            type="date"
            value={catalogFilters.fecha_inicio ?? ""}
          />
          <Input
            label="Fecha fin"
            onChange={(event) => {
              setCatalogFilters((current) => ({
                ...current,
                fecha_fin: event.target.value || undefined,
              }));
              setOperativoFilters((current) => ({
                ...current,
                fecha_hasta: event.target.value || undefined,
              }));
            }}
            type="date"
            value={catalogFilters.fecha_fin ?? ""}
          />

          {activeTab === "operadores" ? (
            <SearchableSelect
              emptyLabel="Todos los operadores"
              label="Selecciona operador"
              onChange={(value) => {
                setOperatorSearch(value);
                const match = findLookupMatch(value, operadoresOptions);
                setCatalogFilters((current) => ({
                  ...current,
                  id_operador: match?.id,
                  nombre_operador: value.trim() || undefined,
                }));
              }}
              options={operadoresOptions.map((option) => ({
                value: String(option.id),
                label: option.label,
                description: option.description,
              }))}
              placeholder="Busca por nombre del operador"
              value={operatorSearch}
            />
          ) : activeTab === "trailers" ? (
            <SearchableSelect
              emptyLabel="Todos los tráilers"
              label="Selecciona tráiler"
              onChange={(value) => {
                setTrailerSearch(value);
                const match = findLookupMatch(value, trailersOptions);
                setCatalogFilters((current) => ({
                  ...current,
                  id_trailer: match?.id,
                  numero_economico: value.trim() || undefined,
                }));
              }}
              options={trailersOptions.map((option) => ({
                value: String(option.id),
                label: option.label,
                description: option.description,
              }))}
              placeholder="Busca por número económico"
              value={trailerSearch}
            />
          ) : activeTab === "clientes" ? (
            <SearchableSelect
              emptyLabel="Todos los clientes"
              label="Selecciona cliente"
              onChange={(value) => {
                setClientSearch(value);
                const match = findLookupMatch(value, clientesOptions);
                setCatalogFilters((current) => ({
                  ...current,
                  id_cliente: match?.id,
                  nombre_cliente: value.trim() || undefined,
                }));
              }}
              options={clientesOptions.map((option) => ({
                value: String(option.id),
                label: option.label,
                description: option.description,
              }))}
              placeholder="Busca por razón social"
              value={clientSearch}
            />
          ) : (
            <SearchableSelect
              emptyLabel="Todos los operadores"
              label="Selecciona operador"
              onChange={(value) => {
                const match = findLookupMatch(value, operadoresOptions);
                setOperatorSearch(value);
                setOperativoFilters((current) => ({
                  ...current,
                  id_operador: match?.id,
                }));
              }}
              options={operadoresOptions.map((option) => ({
                value: String(option.id),
                label: option.label,
                description: option.description,
              }))}
              placeholder="Busca por nombre del operador"
              value={operatorSearch}
            />
          )}

          {activeTab === "operativo" ? (
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
              <input
                checked={operativoFilters.solo_completos ?? false}
                onChange={(event) =>
                  setOperativoFilters((current) => ({
                    ...current,
                    solo_completos: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              Solo KPIs completos
            </label>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {activeTab === "trailers"
                ? "El rendimiento se calcula con nivel de diésel porcentual reportado por el operador."
                : "Ajusta el rango y aplica filtros para recalcular los indicadores."}
            </div>
          )}
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Button
            onClick={() => {
              if (activeTab === "operativo") {
                setAppliedOperativoFilters(operativoFilters);
              } else {
                setAppliedCatalogFilters(catalogFilters);
              }
            }}
            type="button"
          >
            Aplicar
          </Button>
          <Button
            onClick={() => {
              setCatalogFilters(initialCatalogFilters);
              setAppliedCatalogFilters(initialCatalogFilters);
              setOperativoFilters(initialOperativoFilters);
              setAppliedOperativoFilters(initialOperativoFilters);
              setOperatorSearch("");
              setTrailerSearch("");
              setClientSearch("");
            }}
            type="button"
            variant="secondary"
          >
            Limpiar
          </Button>
        </div>
      </Card>

      {activeDataEmpty ? <KpiEmptyState description={emptyMessage} /> : null}

      {activeTab === "operadores" && operadoresData ? (
        <>
          <BasicSummaryCards
            items={[
              { label: "Viajes semana", value: operadoresData.total_viajes_semana },
              { label: "Viajes mes", value: operadoresData.total_viajes_mes },
              { label: "KM recorridos", value: operadoresData.total_km_recorridos },
            ]}
          />
          <div className="grid gap-4 lg:grid-cols-2">
            <SeriesCard
              items={operadoresData.series_semanales}
              subtitle="Viajes registrados por semana"
              title="Serie semanal"
            />
            <SeriesCard
              items={operadoresData.series_mensuales}
              subtitle="Viajes registrados por mes"
              title="Serie mensual"
            />
          </div>
          <Card className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Nombre operador", "Viajes semana", "Viajes mes", "KM recorridos"].map(
                    (header) => (
                      <th
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                        key={header}
                      >
                        {header}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {operadoresData.operadores.map((operador) => (
                  <tr className="border-t border-slate-100" key={operador.id_operador}>
                    <td className="px-4 py-4 font-medium text-slate-950">
                      <div>{operador.nombre_completo ?? operador.nombre_operador}</div>
                      {operador.nombre_completo ? (
                        <p className="mt-1 text-xs text-slate-500">{operador.nombre_operador}</p>
                      ) : null}
                    </td>
                    <td className="px-4 py-4 text-slate-700">{operador.viajes_semana}</td>
                    <td className="px-4 py-4 text-slate-700">{operador.viajes_mes}</td>
                    <td className="px-4 py-4 text-slate-700">
                      {formatNumber(operador.km_recorridos)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      ) : null}

      {activeTab === "trailers" && trailersData ? (
        <>
          <BasicSummaryCards
            items={[
              { label: "KM recorridos", value: trailersData.total_km_recorridos },
              { label: "Diésel consumido (%)", value: trailersData.total_diesel_consumido_pct },
              {
                label: "Rendimiento promedio",
                value: trailersData.rendimiento_promedio_km_por_pct_diesel,
              },
            ]}
          />
          <Card className="p-5 text-sm text-slate-600">
            El rendimiento se calcula con nivel de diésel porcentual reportado por el operador.
          </Card>
          <Card className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {[
                    "Número económico",
                    "Placas",
                    "KM recorridos",
                    "Diésel consumido (%)",
                    "Rendimiento km/% diésel",
                  ].map((header) => (
                    <th
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                      key={header}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trailersData.trailers.map((trailer) => (
                  <tr className="border-t border-slate-100" key={trailer.id_trailer}>
                    <td className="px-4 py-4 font-medium text-slate-950">
                      {trailer.numero_economico}
                    </td>
                    <td className="px-4 py-4 text-slate-700">{trailer.placas ?? "Sin dato"}</td>
                    <td className="px-4 py-4 text-slate-700">{formatNumber(trailer.km_recorridos)}</td>
                    <td className="px-4 py-4 text-slate-700">
                      {formatNumber(trailer.diesel_consumido_pct)}
                    </td>
                    <td className="px-4 py-4 text-slate-700">
                      {formatNumber(trailer.rendimiento_km_por_pct_diesel)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <Card className="overflow-x-auto">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-slate-950">Detalle por viaje / tráiler</h2>
            </div>
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {[
                    "Número económico",
                    "Viaje",
                    "KM",
                    "Diésel (%)",
                    "Rendimiento",
                    "Estado consumo",
                  ].map((header) => (
                    <th
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                      key={header}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trailersData.trailers.flatMap((trailer) =>
                  trailer.viajes.map((viaje) => (
                    <tr
                      className="border-t border-slate-100"
                      key={`${trailer.id_trailer}-${viaje.id_viaje}`}
                    >
                      <td className="px-4 py-4 font-medium text-slate-950">
                        {viaje.numero_economico}
                      </td>
                      <td className="px-4 py-4 text-slate-700">{viaje.folio}</td>
                      <td className="px-4 py-4 text-slate-700">{formatNumber(viaje.km_recorridos)}</td>
                      <td className="px-4 py-4 text-slate-700">
                        {formatNumber(viaje.diesel_consumido_pct)}
                      </td>
                      <td className="px-4 py-4 text-slate-700">
                        {formatNumber(viaje.rendimiento_km_por_pct_diesel)}
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge variant={viaje.consumo_valido ? "success" : "warning"}>
                          {viaje.consumo_valido ? "Consumo válido" : "Sin consumo válido"}
                        </StatusBadge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </Card>
        </>
      ) : null}

      {activeTab === "clientes" && clientesData ? (
        <>
          <BasicSummaryCards
            items={[
              { label: "Terminados semana", value: clientesData.total_viajes_terminados_semana },
              { label: "Terminados mes", value: clientesData.total_viajes_terminados_mes },
              { label: "Viajes en espera", value: clientesData.total_viajes_en_espera },
            ]}
          />
          <div className="grid gap-4 lg:grid-cols-2">
            <SeriesCard
              items={clientesData.series_semanales}
              subtitle="Viajes finalizados por semana"
              title="Serie semanal"
            />
            <SeriesCard
              items={clientesData.series_mensuales}
              subtitle="Viajes finalizados por mes"
              title="Serie mensual"
            />
          </div>
          <Card className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Cliente", "Terminados semana", "Terminados mes", "Viajes en espera"].map(
                    (header) => (
                      <th
                        className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                        key={header}
                      >
                        {header}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {clientesData.clientes.map((cliente) => (
                  <tr className="border-t border-slate-100" key={cliente.id_cliente}>
                    <td className="px-4 py-4 font-medium text-slate-950">
                      {cliente.nombre_razon_social}
                    </td>
                    <td className="px-4 py-4 text-slate-700">
                      {cliente.viajes_terminados_semana}
                    </td>
                    <td className="px-4 py-4 text-slate-700">
                      {cliente.viajes_terminados_mes}
                    </td>
                    <td className="px-4 py-4 text-slate-700">{cliente.viajes_en_espera}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      ) : null}

      {activeTab === "operativo" && operativoData ? (
        <>
          <KpiSummaryCards resumen={operativoData.resumen} />
          {operativoData.viajes.length === 0 ? (
            <KpiEmptyState description={emptyMessage} />
          ) : (
            <KpiTripTable rows={operativoData.viajes} />
          )}
        </>
      ) : null}
    </div>
  );
}
