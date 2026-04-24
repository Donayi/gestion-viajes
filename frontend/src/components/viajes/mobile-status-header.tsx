import Link from "next/link";

import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import type { ViajeDetail } from "@/types/viaje";

export function MobileStatusHeader({ viaje }: { viaje: ViajeDetail }) {
  return (
    <section className="rounded-[2rem] border border-white/10 bg-gradient-to-br from-brand-700 via-brand-800 to-slate-950 p-5 text-white shadow-soft">
      <Link className="text-sm font-medium text-brand-100" href="/viajes">
        ← Volver a viajes
      </Link>

      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-100">
            {viaje.folio}
          </p>
          <h1 className="mt-2 text-3xl font-semibold">{viaje.cliente.nombre_razon_social}</h1>
        </div>
        <div className="rounded-full bg-white/10 px-2 py-1">
          <ViajeStatusBadge
            clave={viaje.estatus_actual.clave}
            nombre={viaje.estatus_actual.nombre}
          />
        </div>
      </div>
    </section>
  );
}
