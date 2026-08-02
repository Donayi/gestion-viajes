import Link from "next/link";
import {
  ArrowUpRight,
  Boxes,
  Map,
  RefreshCcw,
  ShieldCheck,
  Truck,
  UserRound,
} from "lucide-react";

import { DashboardAlertList } from "@/components/dashboard/dashboard-alert-list";
import { DashboardAvailabilityPanel } from "@/components/dashboard/dashboard-availability-panel";
import { DashboardKpiGrid } from "@/components/dashboard/dashboard-kpi-grid";
import { DashboardMaintenanceList } from "@/components/dashboard/dashboard-maintenance-list";
import { DashboardSectionCard } from "@/components/dashboard/dashboard-section-card";
import { DashboardStatusOverview } from "@/components/dashboard/dashboard-status-overview";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { ViajeOperativoMap } from "@/components/viajes/viaje-operativo-map";
import { formatDateTime as formatProjectDateTime } from "@/lib/formatters";
import type { CurrentUser } from "@/types/auth";
import type { AdminDashboardResponse } from "@/types/dashboard";

function formatNumber(value: number, options?: Intl.NumberFormatOptions) {
  return new Intl.NumberFormat("es-MX", options).format(value);
}

function formatDecimal(value: number) {
  return new Intl.NumberFormat("es-MX", {
    maximumFractionDigits: 1,
    minimumFractionDigits: value % 1 === 0 ? 0 : 1,
  }).format(value);
}

function formatGeneratedAt(value: string) {
  try {
    const parsedDate = new Date(value);
    if (Number.isNaN(parsedDate.getTime())) {
      return "Sin fecha disponible";
    }
    return formatProjectDateTime(value);
  } catch {
    return "Sin fecha disponible";
  }
}

export function AdminDashboard({
  dashboard,
  user,
  refreshing,
  onRefresh,
}: {
  dashboard: AdminDashboardResponse;
  user: CurrentUser | null;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const emptyDashboard =
    dashboard.viajes_resumen.total === 0 &&
    dashboard.alertas.pendientes_total === 0 &&
    dashboard.mantenimientos.abiertos_total === 0 &&
    dashboard.mantenimientos.en_proceso_total === 0 &&
    dashboard.mantenimientos.proximos_total === 0;

  const userName = `${user?.nombre ?? ""} ${user?.apellido ?? ""}`.trim() || "Administrador";

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[2rem] border border-brand-100 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.18),_transparent_32%),linear-gradient(135deg,_#0f172a_0%,_#111827_45%,_#1e3a8a_100%)] p-6 text-white shadow-soft md:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-4">
            <StatusBadge className="border-white/15 bg-white/10 text-white" variant="neutral">
              Dashboard Enterprise ADMIN
            </StatusBadge>
            <div className="space-y-3">
              <p className="text-sm font-medium text-sky-100">
                Visibilidad integral de viajes, alertas, mantenimientos y disponibilidad.
              </p>
              <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
                Centro operativo DAFREQ
              </h1>
              <p className="max-w-2xl text-sm leading-6 text-slate-200 md:text-base">
                Hola, {userName}. Este tablero concentra el panorama ejecutivo actual para tomar
                decisiones rápidas sin salir de la operación.
              </p>
            </div>
          </div>

          <div className="flex flex-col items-start gap-3 rounded-[1.5rem] border border-white/10 bg-white/10 p-4 backdrop-blur">
            <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.18em] text-sky-100">
              <ShieldCheck className="h-4 w-4" />
              <span>Actualización del tablero</span>
            </div>
            <p className="text-lg font-semibold">{formatGeneratedAt(dashboard.generated_at)}</p>
            <p className="text-sm text-slate-200">
              Usuario: {user?.username ?? "Sin sesión"} · Rol: {user?.rol ?? "N/D"}
            </p>
            <Button
              className="w-full border-white/10 bg-white text-slate-950 hover:bg-slate-100"
              disabled={refreshing}
              onClick={onRefresh}
              type="button"
              variant="secondary"
            >
              <RefreshCcw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "Actualizando..." : "Actualizar"}
            </Button>
          </div>
        </div>
      </section>

      <DashboardKpiGrid dashboard={dashboard} />

      <section className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <DashboardSectionCard
          action={
            <Link
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2"
              href="/admin/mapa-viajes"
            >
              Ver mapa completo
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          }
          description="Última ubicación operativa conocida de los viajes visibles para administración."
          eyebrow="Mapa operativo"
          title="Seguimiento geográfico"
        >
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Con ubicación
                </p>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {formatNumber(dashboard.mapa.total_con_ubicacion)}
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Sin ubicación
                </p>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {formatNumber(dashboard.mapa.total_sin_ubicacion)}
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Viajes activos
                </p>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {formatNumber(dashboard.viajes_resumen.activos)}
                </p>
              </div>
            </div>
            <ViajeOperativoMap compact viajes={dashboard.mapa.items} />
          </div>
        </DashboardSectionCard>

        <div className="space-y-6">
          <DashboardSectionCard
            description="Distribución actual del universo visible en el dashboard."
            eyebrow="Viajes"
            title="Resumen por estatus"
          >
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center gap-2 text-slate-500">
                    <Truck className="h-4 w-4" />
                    <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                      Activos
                    </p>
                  </div>
                  <p className="mt-2 text-3xl font-semibold text-slate-950">
                    {formatNumber(dashboard.viajes_resumen.activos)}
                  </p>
                </div>
                <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center gap-2 text-slate-500">
                    <Map className="h-4 w-4" />
                    <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                      Standby
                    </p>
                  </div>
                  <p className="mt-2 text-3xl font-semibold text-slate-950">
                    {formatNumber(dashboard.viajes_resumen.standby)}
                  </p>
                </div>
              </div>

              <DashboardStatusOverview
                items={dashboard.viajes_resumen.por_estatus}
                total={dashboard.viajes_resumen.total}
              />
            </div>
          </DashboardSectionCard>

          <DashboardSectionCard
            description="Vista ejecutiva de los indicadores operativos disponibles en el backend agregado."
            eyebrow="KPIs"
            title="Indicadores operativos"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Viajes con eventos
                </p>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {formatNumber(dashboard.kpis_operativos.total_viajes_con_eventos)}
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Diesel estimado
                </p>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {formatDecimal(dashboard.kpis_operativos.diesel_total_consumido_estimado)}
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Km promedio por viaje
                </p>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {formatDecimal(dashboard.kpis_operativos.km_promedio_por_viaje)}
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Viajes con KPI válido
                </p>
                <p className="mt-2 text-3xl font-semibold text-slate-950">
                  {formatNumber(dashboard.kpis_operativos.viajes_finalizados_con_kpi)}
                </p>
              </div>
            </div>
          </DashboardSectionCard>
        </div>
      </section>

      <DashboardSectionCard
        description="Disponibilidad actual consolidada de los recursos operativos del sistema."
        eyebrow="Capacidad"
        title="Disponibilidad de recursos"
      >
        <DashboardAvailabilityPanel disponibilidad={dashboard.disponibilidad} />
      </DashboardSectionCard>

      <section className="grid gap-6 xl:grid-cols-2">
        <DashboardSectionCard
          description="Alertas operativas priorizadas para revisión administrativa inmediata."
          eyebrow="Alertas"
          title="Bandeja prioritaria"
        >
          <DashboardAlertList
            criticasNoLeidas={dashboard.alertas.criticas_no_leidas}
            items={dashboard.alertas.items}
            pendientesTotal={dashboard.alertas.pendientes_total}
          />
        </DashboardSectionCard>

        <DashboardSectionCard
          description="Intervenciones activas o próximas sobre tráilers y cajas."
          eyebrow="Mantenimiento"
          title="Seguimiento de taller"
        >
          <DashboardMaintenanceList
            abiertosTotal={dashboard.mantenimientos.abiertos_total}
            enProcesoTotal={dashboard.mantenimientos.en_proceso_total}
            items={dashboard.mantenimientos.items}
            proximosTotal={dashboard.mantenimientos.proximos_total}
          />
        </DashboardSectionCard>
      </section>

      {emptyDashboard ? (
        <DashboardSectionCard
          description="El sistema está listo para mostrar información en cuanto haya actividad."
          eyebrow="Sin actividad"
          title="Tablero en espera"
        >
          <div className="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-sm text-slate-500">
            No hay viajes, alertas ni mantenimientos activos para representar en este momento.
          </div>
        </DashboardSectionCard>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-3 text-slate-500">
            <UserRound className="h-5 w-5" />
            <p className="text-sm font-medium">Usuario actual</p>
          </div>
          <p className="mt-3 text-xl font-semibold text-slate-950">{userName}</p>
          <p className="mt-1 text-sm text-slate-600">{user?.username ?? "Sin usuario"}</p>
        </div>
        <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-3 text-slate-500">
            <Boxes className="h-5 w-5" />
            <p className="text-sm font-medium">Cajas disponibles</p>
          </div>
          <p className="mt-3 text-xl font-semibold text-slate-950">
            {formatNumber(dashboard.disponibilidad.cajas.disponibles)}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {formatNumber(dashboard.disponibilidad.cajas.en_mantenimiento)} en mantenimiento
          </p>
        </div>
        <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex items-center gap-3 text-slate-500">
            <Truck className="h-5 w-5" />
            <p className="text-sm font-medium">Tráilers disponibles</p>
          </div>
          <p className="mt-3 text-xl font-semibold text-slate-950">
            {formatNumber(dashboard.disponibilidad.trailers.disponibles)}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {formatNumber(dashboard.disponibilidad.trailers.en_mantenimiento)} en mantenimiento
          </p>
        </div>
      </section>
    </div>
  );
}
