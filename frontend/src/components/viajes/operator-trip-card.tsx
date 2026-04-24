import Link from "next/link";

import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import type { ViajeListItem } from "@/types/viaje";

export function OperatorTripCard({ viaje }: { viaje: ViajeListItem }) {
  return (
    <article className="rounded-[1.75rem] border border-white/10 bg-white p-5 shadow-soft">
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

      <div className="mt-5 rounded-[1.5rem] bg-slate-50 p-4">
        <div className="flex gap-4">
          <div className="flex flex-col items-center">
            <span className="h-3 w-3 rounded-full bg-brand-600" />
            <span className="h-12 w-px bg-brand-200" />
            <span className="h-3 w-3 rounded-full bg-slate-900" />
          </div>
          <div className="space-y-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Origen</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{viaje.lugar_inicio}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Destino</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{viaje.lugar_destino}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-2 text-sm text-slate-700">
        <p>Trailer: {viaje.trailer_actual?.numero_economico ?? "Sin asignar"}</p>
        <p>Caja: {viaje.caja_actual?.numero_economico ?? viaje.caja_actual?.placas ?? "Sin asignar"}</p>
      </div>

      <Link
        className="mt-5 inline-flex w-full items-center justify-center rounded-[1.25rem] bg-brand-700 px-5 py-4 text-base font-semibold text-white"
        href={`/viajes/${viaje.id_viaje}`}
      >
        Abrir
      </Link>
    </article>
  );
}
