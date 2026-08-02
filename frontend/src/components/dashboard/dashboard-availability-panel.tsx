import { StatusBadge } from "@/components/ui/status-badge";
import type { AdminDashboardDisponibilidad } from "@/types/dashboard";

type AvailabilityCardProps = {
  title: string;
  total: number;
  rows: Array<{
    label: string;
    value: number;
    variant: Parameters<typeof StatusBadge>[0]["variant"];
  }>;
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("es-MX").format(value);
}

function AvailabilityCard({ title, total, rows }: AvailabilityCardProps) {
  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{title}</p>
          <p className="text-xs text-slate-500">Total registrado: {formatNumber(total)}</p>
        </div>
        <StatusBadge variant="neutral">{formatNumber(total)}</StatusBadge>
      </div>

      <div className="mt-4 space-y-3">
        {rows.map((row) => {
          const ratio = total > 0 ? Math.min((row.value / total) * 100, 100) : 0;
          return (
            <div className="space-y-2" key={`${title}-${row.label}`}>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-slate-700">{row.label}</span>
                <StatusBadge variant={row.variant}>{formatNumber(row.value)}</StatusBadge>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white">
                <div
                  className="h-full rounded-full bg-brand-700 transition-[width]"
                  style={{ width: `${ratio}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DashboardAvailabilityPanel({
  disponibilidad,
}: {
  disponibilidad: AdminDashboardDisponibilidad;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <AvailabilityCard
        title="Operadores"
        total={disponibilidad.operadores.total}
        rows={[
          {
            label: "Disponibles",
            value: disponibilidad.operadores.disponibles,
            variant: "success",
          },
          {
            label: "Ocupados",
            value: disponibilidad.operadores.ocupados,
            variant: "info",
          },
          {
            label: "Inactivos",
            value: disponibilidad.operadores.inactivos,
            variant: "inactive",
          },
        ]}
      />
      <AvailabilityCard
        title="Tráilers"
        total={disponibilidad.trailers.total}
        rows={[
          {
            label: "Disponibles",
            value: disponibilidad.trailers.disponibles,
            variant: "success",
          },
          {
            label: "Ocupados",
            value: disponibilidad.trailers.ocupados,
            variant: "info",
          },
          {
            label: "En mantenimiento",
            value: disponibilidad.trailers.en_mantenimiento,
            variant: "warning",
          },
          {
            label: "Inactivos",
            value: disponibilidad.trailers.inactivos,
            variant: "inactive",
          },
        ]}
      />
      <AvailabilityCard
        title="Cajas"
        total={disponibilidad.cajas.total}
        rows={[
          {
            label: "Disponibles",
            value: disponibilidad.cajas.disponibles,
            variant: "success",
          },
          {
            label: "Ocupadas",
            value: disponibilidad.cajas.ocupadas,
            variant: "info",
          },
          {
            label: "En mantenimiento",
            value: disponibilidad.cajas.en_mantenimiento,
            variant: "warning",
          },
          {
            label: "Inactivas",
            value: disponibilidad.cajas.inactivas,
            variant: "inactive",
          },
        ]}
      />
    </div>
  );
}
