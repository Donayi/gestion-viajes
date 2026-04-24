import Link from "next/link";

import { Card } from "@/components/ui/card";
import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import type { ViajeListItem } from "@/types/viaje";

function ResourceLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-800">{value}</span>
    </div>
  );
}

export function ViajeCard({ viaje }: { viaje: ViajeListItem }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
            {viaje.folio}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-950">
            {viaje.cliente.nombre_razon_social}
          </h3>
        </div>
        <ViajeStatusBadge
          clave={viaje.estatus_actual.clave}
          nombre={viaje.estatus_actual.nombre}
        />
      </div>

      <div className="mt-5 space-y-3">
        <ResourceLine label="Origen" value={viaje.lugar_inicio} />
        <ResourceLine label="Destino" value={viaje.lugar_destino} />
        <ResourceLine label="Operador" value={viaje.operador_actual?.alias ?? "Sin asignar"} />
        <ResourceLine
          label="Trailer"
          value={viaje.trailer_actual?.numero_economico ?? "Sin asignar"}
        />
        <ResourceLine
          label="Caja"
          value={viaje.caja_actual?.numero_economico ?? viaje.caja_actual?.placas ?? "Sin asignar"}
        />
      </div>

      <Link
        className="mt-5 inline-flex rounded-2xl bg-brand-700 px-4 py-2.5 text-sm font-medium text-white"
        href={`/viajes/${viaje.id_viaje}`}
      >
        Ver detalle
      </Link>
    </Card>
  );
}
