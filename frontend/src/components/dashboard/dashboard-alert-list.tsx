import Link from "next/link";
import { BellRing, ChevronRight } from "lucide-react";

import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateTime } from "@/lib/formatters";
import type { AdminDashboardAlertItem } from "@/types/dashboard";

const variantMap: Record<string, Parameters<typeof StatusBadge>[0]["variant"]> = {
  INFO: "info",
  WARNING: "warning",
  CRITICAL: "danger",
};

function formatTipo(tipo: string) {
  return tipo.replaceAll("_", " ");
}

function formatAlertDate(value: string | null | undefined) {
  if (!value) {
    return "Fecha no disponible";
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return "Fecha no disponible";
  }

  return formatDateTime(value);
}

export function DashboardAlertList({
  items,
  pendientesTotal,
  criticasNoLeidas,
}: {
  items: AdminDashboardAlertItem[];
  pendientesTotal: number;
  criticasNoLeidas: number;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Pendientes
          </p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{pendientesTotal}</p>
        </div>
        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Críticas sin leer
          </p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{criticasNoLeidas}</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No hay alertas prioritarias en este momento.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              className="rounded-[1.5rem] border border-slate-200 bg-white p-4"
              key={item.id_alerta}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge variant={variantMap[item.nivel] ?? "neutral"}>
                      {item.nivel}
                    </StatusBadge>
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      {formatTipo(item.tipo_alerta)}
                    </span>
                  </div>
                  <p className="text-sm leading-6 text-slate-700">{item.mensaje}</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span>
                      {item.entidad_tipo} #{item.entidad_id}
                    </span>
                    <span>{formatAlertDate(item.created_at)}</span>
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-2 text-slate-500">
                  <BellRing className="h-4 w-4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Link
        className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2 sm:w-auto"
        href="/admin/alertas"
      >
        Ver alertas
        <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
