"use client";

import dynamic from "next/dynamic";

type ViajeRouteMapProps = {
  origen: {
    direccion: string;
    latitud: number | null;
    longitud: number | null;
  };
  destino: {
    direccion: string;
    latitud: number | null;
    longitud: number | null;
  };
};

const ViajeRouteMapClient = dynamic(
  () => import("./viaje-route-map-client").then((module) => module.ViajeRouteMapClient),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-[1.75rem] border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-500 shadow-soft">
        Cargando mapa de ubicaciones del viaje...
      </div>
    ),
  }
);

export function ViajeRouteMap(props: ViajeRouteMapProps) {
  return (
    <ViajeRouteMapClient
      destino={{ ...props.destino, label: "Destino" }}
      origen={{ ...props.origen, label: "Inicio" }}
    />
  );
}
