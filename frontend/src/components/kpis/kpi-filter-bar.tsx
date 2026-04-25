"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { isAdmin } from "@/lib/permissions";
import type { CurrentUser } from "@/types/auth";
import type { KpiOperativoFilters } from "@/types/kpi";

export function KpiFilterBar({
  filters,
  onChange,
  onApply,
  onReset,
  user
}: {
  filters: KpiOperativoFilters;
  onChange: (next: KpiOperativoFilters) => void;
  onApply: () => void;
  onReset: () => void;
  user: CurrentUser | null;
}) {
  const admin = isAdmin(user);

  return (
    <Card className="border-brand-100 p-5">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
          Filtros
        </p>
        <h2 className="text-xl font-semibold text-slate-950">KPIs operativos</h2>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Input
          label="Fecha desde"
          onChange={(event) => onChange({ ...filters, fecha_desde: event.target.value || undefined })}
          type="date"
          value={filters.fecha_desde ?? ""}
        />
        <Input
          label="Fecha hasta"
          onChange={(event) => onChange({ ...filters, fecha_hasta: event.target.value || undefined })}
          type="date"
          value={filters.fecha_hasta ?? ""}
        />
        {admin ? (
          <Input
            label="ID operador"
            onChange={(event) =>
              onChange({
                ...filters,
                id_operador: event.target.value ? Number(event.target.value) : undefined
              })
            }
            type="number"
            value={filters.id_operador ?? ""}
          />
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-sm font-medium text-slate-700">Operador</p>
            <p className="mt-2 text-sm text-slate-500">Mostrando solo tus viajes</p>
          </div>
        )}
        <Input
          label="ID cliente"
          onChange={(event) =>
            onChange({
              ...filters,
              id_cliente: event.target.value ? Number(event.target.value) : undefined
            })
          }
          type="number"
          value={filters.id_cliente ?? ""}
        />
        <Input
          label="ID estatus"
          onChange={(event) =>
            onChange({
              ...filters,
              id_estatus: event.target.value ? Number(event.target.value) : undefined
            })
          }
          type="number"
          value={filters.id_estatus ?? ""}
        />
        <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
          <input
            checked={filters.solo_completos ?? false}
            onChange={(event) => onChange({ ...filters, solo_completos: event.target.checked })}
            type="checkbox"
          />
          Solo KPIs completos
        </label>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button onClick={onApply} type="button">
          Aplicar filtros
        </Button>
        <Button onClick={onReset} type="button" variant="secondary">
          Limpiar
        </Button>
      </div>
    </Card>
  );
}
