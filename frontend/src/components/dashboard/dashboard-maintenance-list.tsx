import Link from "next/link";
import { ChevronRight, Wrench } from "lucide-react";

import { StatusBadge } from "@/components/ui/status-badge";
import { formatDate } from "@/lib/formatters";
import type { AdminDashboardMaintenanceItem } from "@/types/dashboard";

const variantMap: Record<string, Parameters<typeof StatusBadge>[0]["variant"]> = {
  ABIERTO: "warning",
  EN_PROCESO: "info",
  CERRADO: "success",
  CANCELADO: "inactive",
};

function formatMaintenanceDate(value: string | null | undefined) {
  if (!value) {
    return "Sin programación";
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return "Fecha no disponible";
  }

  return formatDate(value);
}

export function DashboardMaintenanceList({
  items,
  abiertosTotal,
  enProcesoTotal,
  proximosTotal,
}: {
  items: AdminDashboardMaintenanceItem[];
  abiertosTotal: number;
  enProcesoTotal: number;
  proximosTotal: number;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Abiertos
          </p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{abiertosTotal}</p>
        </div>
        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            En proceso
          </p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{enProcesoTotal}</p>
        </div>
        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Próximos
          </p>
          <p className="mt-2 text-3xl font-semibold text-slate-950">{proximosTotal}</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          No hay mantenimientos activos o próximos para mostrar.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              className="rounded-[1.5rem] border border-slate-200 bg-white p-4"
              key={item.id_mantenimiento}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge variant={variantMap[item.estatus] ?? "neutral"}>
                      {item.estatus}
                    </StatusBadge>
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      {item.tipo_mantenimiento}
                    </span>
                  </div>
                  <div>
                    <p className="font-semibold text-slate-950">{item.entidad.etiqueta}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      {item.entidad.subtitulo ?? item.descripcion}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span>Inicio: {formatMaintenanceDate(item.fecha_inicio)}</span>
                    <span>Próximo: {formatMaintenanceDate(item.fecha_proximo_mantenimiento)}</span>
                  </div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-2 text-slate-500">
                  <Wrench className="h-4 w-4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Link
        className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2 sm:w-auto"
        href="/admin/mantenimientos"
      >
        Ver mantenimientos
        <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
