import { StatusBadge } from "@/components/ui/status-badge";
import type { DashboardStatusCount } from "@/types/dashboard";

const variantMap: Record<string, Parameters<typeof StatusBadge>[0]["variant"]> = {
  CREADO: "neutral",
  ASIGNADO: "info",
  CARGANDO: "primary",
  INICIADO: "primary",
  RETRASADO: "warning",
  STANDBY: "warning",
  FINALIZADO: "success",
  CANCELADO: "danger",
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("es-MX").format(value);
}

export function DashboardStatusOverview({
  items,
  total,
}: {
  items: DashboardStatusCount[];
  total: number;
}) {
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
        No hay estatus de viaje disponibles para mostrar.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item) => {
        const ratio = total > 0 ? Math.min((item.total / total) * 100, 100) : 0;

        return (
          <div className="space-y-2" key={`${item.clave}-${item.total}`}>
            <div className="flex items-center justify-between gap-3">
              <StatusBadge variant={variantMap[item.clave] ?? "neutral"}>
                {item.nombre}
              </StatusBadge>
              <span className="text-sm font-medium text-slate-700">
                {formatNumber(item.total)}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand-700 transition-[width]"
                style={{ width: `${ratio}%` }}
              />
            </div>
            <p className="text-xs text-slate-500">{ratio.toFixed(1)}% del total visible</p>
          </div>
        );
      })}
    </div>
  );
}
