import {
  AlertTriangle,
  Clock3,
  Gauge,
  MapPinned,
  PackageCheck,
  ShieldAlert,
  Truck,
  Users,
} from "lucide-react";

import { Card } from "@/components/ui/card";
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

export function DashboardKpiGrid({
  dashboard,
}: {
  dashboard: AdminDashboardResponse;
}) {
  const cards = [
    {
      label: "Total de viajes",
      value: formatNumber(dashboard.viajes_resumen.total),
      helper: `${formatNumber(dashboard.viajes_resumen.activos)} activos y ${formatNumber(
        dashboard.viajes_resumen.finalizados
      )} finalizados`,
      icon: Truck,
      accent: "bg-blue-50 text-blue-700",
    },
    {
      label: "Alertas pendientes",
      value: formatNumber(dashboard.alertas.pendientes_total),
      helper: `${formatNumber(dashboard.alertas.criticas_no_leidas)} críticas sin leer`,
      icon: AlertTriangle,
      accent: "bg-amber-50 text-amber-700",
    },
    {
      label: "Mantenimientos activos",
      value: formatNumber(
        dashboard.mantenimientos.abiertos_total + dashboard.mantenimientos.en_proceso_total
      ),
      helper: `${formatNumber(dashboard.mantenimientos.proximos_total)} próximos`,
      icon: Clock3,
      accent: "bg-emerald-50 text-emerald-700",
    },
    {
      label: "Operadores disponibles",
      value: formatNumber(dashboard.disponibilidad.operadores.disponibles),
      helper: `${formatNumber(dashboard.disponibilidad.operadores.ocupados)} ocupados`,
      icon: Users,
      accent: "bg-sky-50 text-sky-700",
    },
    {
      label: "Kilómetros recorridos",
      value: formatDecimal(dashboard.kpis_operativos.km_total_recorridos),
      helper: `${formatDecimal(
        dashboard.kpis_operativos.km_promedio_por_viaje
      )} km promedio por viaje`,
      icon: Gauge,
      accent: "bg-violet-50 text-violet-700",
    },
    {
      label: "Standbys registrados",
      value: formatNumber(dashboard.kpis_operativos.numero_total_standbys),
      helper: `${formatNumber(dashboard.viajes_resumen.standby)} viajes en standby actual`,
      icon: ShieldAlert,
      accent: "bg-orange-50 text-orange-700",
    },
    {
      label: "Viajes con ubicación",
      value: formatNumber(dashboard.mapa.total_con_ubicacion),
      helper: `${formatNumber(dashboard.mapa.total_sin_ubicacion)} pendientes de ubicación`,
      icon: MapPinned,
      accent: "bg-cyan-50 text-cyan-700",
    },
    {
      label: "Viajes con KPI válido",
      value: formatNumber(dashboard.kpis_operativos.viajes_finalizados_con_kpi),
      helper: `${formatDecimal(
        dashboard.kpis_operativos.diesel_total_consumido_estimado
      )} % diésel estimado`,
      icon: PackageCheck,
      accent: "bg-teal-50 text-teal-700",
    },
  ];

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;

        return (
          <Card className="overflow-hidden p-5" key={card.label}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-slate-500">{card.label}</p>
                <p className="mt-3 text-3xl font-semibold text-slate-950">{card.value}</p>
              </div>
              <div
                className={`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${card.accent}`}
              >
                <Icon className="h-5 w-5" />
              </div>
            </div>
            <p className="mt-4 text-sm text-slate-600">{card.helper}</p>
          </Card>
        );
      })}
    </section>
  );
}
