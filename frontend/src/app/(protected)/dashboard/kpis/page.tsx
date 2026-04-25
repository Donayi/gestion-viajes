"use client";

import { useCallback, useEffect, useState } from "react";

import { KpiEmptyState } from "@/components/kpis/kpi-empty-state";
import { KpiFilterBar } from "@/components/kpis/kpi-filter-bar";
import { KpiSummaryCards } from "@/components/kpis/kpi-summary-cards";
import { KpiTripTable } from "@/components/kpis/kpi-trip-table";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useSession } from "@/hooks/use-session";
import { isAdmin } from "@/lib/permissions";
import { getKpisOperativosRequest } from "@/services/kpis.service";
import { ApiError } from "@/services/api-client";
import type { KpiOperativoDashboard, KpiOperativoFilters } from "@/types/kpi";

const initialFilters: KpiOperativoFilters = {
  solo_completos: false
};

export default function KpisDashboardPage() {
  const { user } = useSession();
  const [filters, setFilters] = useState<KpiOperativoFilters>(initialFilters);
  const [appliedFilters, setAppliedFilters] = useState<KpiOperativoFilters>(initialFilters);
  const [data, setData] = useState<KpiOperativoDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getKpisOperativosRequest(appliedFilters);
      setData(response);
    } catch (currentError) {
      const message =
        currentError instanceof ApiError ? currentError.message : "No fue posible cargar los KPIs";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [appliedFilters]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <LoadingState label="Cargando KPIs operativos..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  if (!data) {
    return <ErrorState message="No fue posible cargar la información de KPIs." onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-r from-brand-800 via-brand-700 to-slate-900 px-6 py-7 text-white shadow-soft">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/70">
          Dashboard ejecutivo
        </p>
        <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">KPIs operativos</h1>
            <p className="mt-2 max-w-3xl text-sm text-white/80">
              {isAdmin(user)
                ? "Analiza kilometraje, consumo estimado y standbys por viaje con filtros operativos."
                : "Consulta tus propios indicadores operativos y detecta viajes incompletos o con anomalías."}
            </p>
          </div>
        </div>
      </section>

      <KpiFilterBar
        filters={filters}
        onApply={() => setAppliedFilters(filters)}
        onChange={setFilters}
        onReset={() => {
          setFilters(initialFilters);
          setAppliedFilters(initialFilters);
        }}
        user={user}
      />

      <KpiSummaryCards resumen={data.resumen} />

      {data.viajes.length === 0 ? <KpiEmptyState /> : <KpiTripTable rows={data.viajes} />}
    </div>
  );
}
