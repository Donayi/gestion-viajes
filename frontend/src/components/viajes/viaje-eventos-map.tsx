"use client";

import dynamic from "next/dynamic";

import type { EventoOperativoViaje } from "@/types/viaje";

const ViajeEventosMapClient = dynamic(
  () =>
    import("./viaje-eventos-map-client").then((module) => module.ViajeEventosMapClient),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-[1.75rem] border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-500 shadow-soft">
        Cargando mapa de ubicaciones...
      </div>
    )
  }
);

export function ViajeEventosMap({
  eventos
}: {
  eventos: EventoOperativoViaje[];
}) {
  return <ViajeEventosMapClient eventos={eventos} />;
}
