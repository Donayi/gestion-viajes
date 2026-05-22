"use client";

import dynamic from "next/dynamic";

import type { ViajeMapaItem } from "@/types/viaje";

const ViajeOperativoMapClient = dynamic(
  () =>
    import("./viaje-operativo-map-client").then((module) => module.ViajeOperativoMapClient),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-[1.75rem] border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-500 shadow-soft">
        Cargando mapa operativo...
      </div>
    )
  }
);

export function ViajeOperativoMap({
  viajes
}: {
  viajes: ViajeMapaItem[];
}) {
  return <ViajeOperativoMapClient viajes={viajes} />;
}
