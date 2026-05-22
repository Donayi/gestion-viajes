"use client";

import Link from "next/link";
import { divIcon } from "leaflet";
import type { LatLngBoundsExpression, LatLngTuple } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo } from "react";

import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import { formatDateTime } from "@/lib/formatters";
import type { ViajeMapaItem } from "@/types/viaje";

const DEFAULT_CENTER: LatLngTuple = [25.6866, -100.3161];

type GeoViaje = ViajeMapaItem & {
  lat: number;
  lng: number;
};

function getStatusColors(clave: string) {
  switch (clave) {
    case "CREADO":
      return { fill: "#64748b", border: "#475569" };
    case "ASIGNADO":
      return { fill: "#38bdf8", border: "#0284c7" };
    case "CARGANDO":
      return { fill: "#2563eb", border: "#1d4ed8" };
    case "INICIADO":
      return { fill: "#16a34a", border: "#15803d" };
    case "RETRASADO":
      return { fill: "#f97316", border: "#ea580c" };
    case "STANDBY":
      return { fill: "#eab308", border: "#ca8a04" };
    case "FINALIZADO":
      return { fill: "#166534", border: "#14532d" };
    case "CANCELADO":
      return { fill: "#dc2626", border: "#b91c1c" };
    default:
      return { fill: "#334155", border: "#1e293b" };
  }
}

function buildTripMarkerIcon(clave: string) {
  const colors = getStatusColors(clave);
  return divIcon({
    className: "viaje-operativo-marker-wrapper",
    html: `
      <div style="
        width: 1.2rem;
        height: 1.2rem;
        border-radius: 9999px;
        background: ${colors.fill};
        border: 2px solid ${colors.border};
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.22);
      "></div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -12]
  });
}

function FitBounds({ points }: { points: LatLngTuple[] }) {
  const map = useMap();

  useEffect(() => {
    if (points.length === 0) {
      map.setView(DEFAULT_CENTER, 6);
      return;
    }

    if (points.length === 1) {
      map.setView(points[0], 10);
      return;
    }

    const bounds: LatLngBoundsExpression = points;
    map.fitBounds(bounds, { padding: [32, 32] });
  }, [map, points]);

  return null;
}

export function ViajeOperativoMapClient({
  viajes
}: {
  viajes: ViajeMapaItem[];
}) {
  const viajesConUbicacion = useMemo<GeoViaje[]>(
    () =>
      viajes
        .filter(
          (viaje): viaje is ViajeMapaItem & {
            ultima_ubicacion: NonNullable<ViajeMapaItem["ultima_ubicacion"]>;
          } =>
            viaje.ultima_ubicacion !== null &&
            viaje.ultima_ubicacion.latitud !== null &&
            viaje.ultima_ubicacion.longitud !== null
        )
        .map((viaje) => ({
          ...viaje,
          lat: Number(viaje.ultima_ubicacion!.latitud),
          lng: Number(viaje.ultima_ubicacion!.longitud)
        })),
    [viajes]
  );

  const points = viajesConUbicacion.map((viaje) => [viaje.lat, viaje.lng] as LatLngTuple);

  if (viajesConUbicacion.length === 0) {
    return (
      <div className="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 px-5 py-10 text-center text-sm text-slate-500">
        No hay viajes con ubicación disponible para los filtros seleccionados.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.75rem] border border-slate-200">
      <MapContainer center={points[0] ?? DEFAULT_CENTER} className="h-[60vh] min-h-[420px] w-full" scrollWheelZoom zoom={6}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points} />

        {viajesConUbicacion.map((viaje) => (
          <Marker
            icon={buildTripMarkerIcon(viaje.estatus_actual.clave)}
            key={viaje.id_viaje}
            position={[viaje.lat, viaje.lng]}
          >
            <Popup>
              <div className="space-y-3 text-sm text-slate-800">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold text-slate-950">{viaje.folio}</p>
                  <ViajeStatusBadge clave={viaje.estatus_actual.clave} nombre={viaje.estatus_actual.nombre} />
                </div>
                <p>{viaje.cliente.nombre_razon_social}</p>
                <div className="space-y-1 text-slate-700">
                  <p>Operador: {viaje.operador_actual?.alias ?? "Sin asignar"}</p>
                  <p>Tráiler: {viaje.trailer_actual?.numero_economico ?? "Sin asignar"}</p>
                  <p>
                    Caja: {viaje.caja_actual?.numero_economico ?? viaje.caja_actual?.placas ?? "Sin asignar"}
                  </p>
                  <p>Ubicación: {viaje.ultima_ubicacion?.ubicacion ?? "Sin ubicación"}</p>
                  <p>
                    Último evento: {viaje.ultima_ubicacion?.tipo_evento ?? "Sin referencia"}
                  </p>
                  <p>
                    Última actualización:{" "}
                    {viaje.ultima_ubicacion?.created_at
                      ? formatDateTime(viaje.ultima_ubicacion.created_at)
                      : "Sin fecha"}
                  </p>
                </div>
                <Link
                  className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                  href={`/viajes/${viaje.id_viaje}`}
                >
                  Ver detalle
                </Link>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
