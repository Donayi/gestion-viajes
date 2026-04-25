import { Card } from "@/components/ui/card";
import { formatDateTime } from "@/lib/formatters";
import type { KpiOperativoViajeRow } from "@/types/kpi";

import { KpiStatusPill } from "./kpi-status-pill";

const headers = [
  "Folio",
  "Cliente",
  "Operador",
  "KM inicio",
  "KM final",
  "KM recorridos",
  "Diésel inicio",
  "Diésel final",
  "Diésel consumido",
  "Standbys",
  "Ubicación inicio",
  "Ubicación final",
  "Fecha inicio",
  "Fecha finalización",
  "Estado KPI"
];

export function KpiTripTable({ rows }: { rows: KpiOperativoViajeRow[] }) {
  return (
    <Card className="overflow-hidden border-brand-100">
      <div className="border-b border-slate-200 bg-gradient-to-r from-brand-700 to-brand-600 px-5 py-4 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/70">
          Vista por viaje
        </p>
        <h2 className="mt-2 text-lg font-semibold">KPIs operativos por viaje</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1420px] w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              {headers.map((header) => (
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
            {rows.map((row) => (
              <tr key={row.id_viaje} className="border-t border-slate-100 align-top">
                <td className="px-4 py-4 font-semibold text-slate-950">{row.folio}</td>
                <td className="px-4 py-4 text-slate-700">{row.cliente}</td>
                <td className="px-4 py-4 text-slate-700">{row.operador ?? "Sin dato"}</td>
                <td className="px-4 py-4 text-slate-700">{formatNumber(row.km_inicio)}</td>
                <td className="px-4 py-4 text-slate-700">{formatNumber(row.km_final)}</td>
                <td className="px-4 py-4 text-slate-700">{formatNumber(row.km_recorridos)}</td>
                <td className="px-4 py-4 text-slate-700">{formatNumber(row.diesel_inicio)}</td>
                <td className="px-4 py-4 text-slate-700">{formatNumber(row.diesel_final)}</td>
                <td className="px-4 py-4 text-slate-700">{formatNumber(row.diesel_consumido)}</td>
                <td className="px-4 py-4 text-slate-700">{row.numero_standbys}</td>
                <td className="px-4 py-4 text-slate-700">{row.ubicacion_inicio ?? "Sin dato"}</td>
                <td className="px-4 py-4 text-slate-700">{row.ubicacion_final ?? "Sin dato"}</td>
                <td className="px-4 py-4 text-slate-700">{formatDateTime(row.fecha_inicio)}</td>
                <td className="px-4 py-4 text-slate-700">{formatDateTime(row.fecha_finalizacion)}</td>
                <td className="px-4 py-4">
                  <div className="space-y-2">
                    <KpiStatusPill
                      anomalia={row.anomalia}
                      kpiCompleto={row.kpi_completo}
                      kpiValido={row.kpi_valido}
                    />
                    {row.anomalia ? (
                      <p className="text-xs text-slate-500">{row.anomalia}</p>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function formatNumber(value: number | null) {
  if (value === null) return "Sin dato";
  return value.toLocaleString("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
}
