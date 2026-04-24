import Link from "next/link";

import { Card } from "@/components/ui/card";
import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import type { ViajeListItem } from "@/types/viaje";

export function ViajesTable({ viajes }: { viajes: ViajeListItem[] }) {
  return (
    <Card className="hidden overflow-hidden xl:block">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr className="text-left text-xs uppercase tracking-[0.18em] text-slate-500">
              <th className="px-6 py-4">Folio</th>
              <th className="px-6 py-4">Cliente</th>
              <th className="px-6 py-4">Estatus</th>
              <th className="px-6 py-4">Origen</th>
              <th className="px-6 py-4">Destino</th>
              <th className="px-6 py-4">Operador</th>
              <th className="px-6 py-4">Trailer</th>
              <th className="px-6 py-4">Caja</th>
              <th className="px-6 py-4" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white text-sm">
            {viajes.map((viaje) => (
              <tr key={viaje.id_viaje} className="align-top">
                <td className="px-6 py-4 font-semibold text-slate-900">{viaje.folio}</td>
                <td className="px-6 py-4 text-slate-700">{viaje.cliente.nombre_razon_social}</td>
                <td className="px-6 py-4">
                  <ViajeStatusBadge
                    clave={viaje.estatus_actual.clave}
                    nombre={viaje.estatus_actual.nombre}
                  />
                </td>
                <td className="px-6 py-4 text-slate-700">{viaje.lugar_inicio}</td>
                <td className="px-6 py-4 text-slate-700">{viaje.lugar_destino}</td>
                <td className="px-6 py-4 text-slate-700">{viaje.operador_actual?.alias ?? "-"}</td>
                <td className="px-6 py-4 text-slate-700">
                  {viaje.trailer_actual?.numero_economico ?? "-"}
                </td>
                <td className="px-6 py-4 text-slate-700">
                  {viaje.caja_actual?.numero_economico ?? viaje.caja_actual?.placas ?? "-"}
                </td>
                <td className="px-6 py-4">
                  <Link
                    className="inline-flex rounded-2xl bg-brand-700 px-4 py-2 font-medium text-white"
                    href={`/viajes/${viaje.id_viaje}`}
                  >
                    Ver detalle
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
