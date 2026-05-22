"use client";

import { useEffect, useMemo, useState } from "react";

import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap
} from "react-leaflet";
import { divIcon } from "leaflet";
import type { LatLngBoundsExpression, LatLngTuple } from "leaflet";

import { Card } from "@/components/ui/card";
import { formatDateTime } from "@/lib/formatters";
import type { EventoOperativoViaje } from "@/types/viaje";

const eventLabels: Record<EventoOperativoViaje["tipo_evento"], string> = {
  INICIO_CARGA: "Inicio carga",
  INICIO_VIAJE: "Inicio viaje",
  REINICIO_VIAJE: "Reinicio",
  RETRASO: "Retraso",
  STANDBY_SOLICITADO: "Solicitud standby",
  STANDBY: "Standby",
  FINALIZACION_VIAJE: "Finalización"
};

const orderedEventTypes: EventoOperativoViaje["tipo_evento"][] = [
  "INICIO_CARGA",
  "INICIO_VIAJE",
  "REINICIO_VIAJE",
  "RETRASO",
  "STANDBY",
  "STANDBY_SOLICITADO",
  "FINALIZACION_VIAJE"
];

type GeoEvent = EventoOperativoViaje & {
  lat: number;
  lng: number;
  sequence: number;
};

function getColorByTipoEvento(tipoEvento: EventoOperativoViaje["tipo_evento"]) {
  switch (tipoEvento) {
    case "INICIO_CARGA":
      return { fill: "#2563eb", border: "#1d4ed8" };
    case "INICIO_VIAJE":
      return { fill: "#16a34a", border: "#15803d" };
    case "REINICIO_VIAJE":
      return { fill: "#166534", border: "#14532d" };
    case "RETRASO":
      return { fill: "#f97316", border: "#ea580c" };
    case "STANDBY":
      return { fill: "#64748b", border: "#475569" };
    case "STANDBY_SOLICITADO":
      return { fill: "#eab308", border: "#ca8a04" };
    case "FINALIZACION_VIAJE":
      return { fill: "#dc2626", border: "#b91c1c" };
    default:
      return { fill: "#2563eb", border: "#1d4ed8" };
  }
}

function buildNumberedMarkerIcon(
  sequence: number,
  tipoEvento: EventoOperativoViaje["tipo_evento"]
) {
  const colors = getColorByTipoEvento(tipoEvento);

  return divIcon({
    className: "viaje-evento-marker-wrapper",
    html: `
      <div style="
        width: 2rem;
        height: 2rem;
        border-radius: 9999px;
        background: ${colors.fill};
        border: 2px solid ${colors.border};
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-size: 0.875rem;
        font-weight: 700;
      ">${sequence}</div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16]
  });
}

function FitBounds({ points }: { points: LatLngTuple[] }) {
  const map = useMap();

  useEffect(() => {
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView(points[0], 13);
      return;
    }

    const bounds: LatLngBoundsExpression = points;
    map.fitBounds(bounds, { padding: [32, 32] });
  }, [map, points]);

  return null;
}

export function ViajeEventosMapClient({
  eventos
}: {
  eventos: EventoOperativoViaje[];
}) {
  const [activeFilters, setActiveFilters] = useState<Record<EventoOperativoViaje["tipo_evento"], boolean>>(
    () =>
      Object.fromEntries(
        orderedEventTypes.map((tipoEvento) => [tipoEvento, true])
      ) as Record<EventoOperativoViaje["tipo_evento"], boolean>
  );

  const allGeoEvents = useMemo<Omit<GeoEvent, "sequence">[]>(
    () =>
      eventos
        .filter(
          (evento): evento is EventoOperativoViaje & { latitud: number; longitud: number } =>
            evento.latitud !== null && evento.longitud !== null
        )
        .sort((left, right) => {
          const leftTime = new Date(left.created_at).getTime();
          const rightTime = new Date(right.created_at).getTime();
          if (leftTime === rightTime) {
            return left.id_evento - right.id_evento;
          }
          return leftTime - rightTime;
        })
        .map((evento) => ({
          ...evento,
          lat: Number(evento.latitud),
          lng: Number(evento.longitud)
        })),
    [eventos]
  );

  const geoEvents = useMemo<GeoEvent[]>(
    () =>
      allGeoEvents
        .filter((evento) => activeFilters[evento.tipo_evento])
        .map((evento, index) => ({
          ...evento,
          sequence: index + 1
        })),
    [activeFilters, allGeoEvents]
  );

  const points = geoEvents.map((evento) => [evento.lat, evento.lng] as LatLngTuple);

  function toggleFilter(tipoEvento: EventoOperativoViaje["tipo_evento"]) {
    setActiveFilters((current) => ({
      ...current,
      [tipoEvento]: !current[tipoEvento]
    }));
  }

  return (
    <Card className="p-5 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
            Trazabilidad geográfica
          </p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950">Mapa de ubicaciones registradas</h2>
          <p className="mt-2 text-sm text-slate-600">
            La línea representa el orden cronológico de los reportes con ubicación.
          </p>
        </div>
        <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
          {geoEvents.length}
        </span>
      </div>

      <div className="mt-5 rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Leyenda</p>
        <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-700">
          {orderedEventTypes.map((tipoEvento) => {
            const colors = getColorByTipoEvento(tipoEvento);
            return (
              <div className="flex items-center gap-2" key={tipoEvento}>
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ backgroundColor: colors.fill, border: `1px solid ${colors.border}` }}
                />
                <span>{eventLabels[tipoEvento]}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-5 rounded-[1.5rem] border border-slate-200 bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Filtros</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {orderedEventTypes.map((tipoEvento) => (
            <label className="flex items-center gap-3 text-sm text-slate-700" key={tipoEvento}>
              <input
                checked={activeFilters[tipoEvento]}
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                onChange={() => toggleFilter(tipoEvento)}
                type="checkbox"
              />
              <span>{eventLabels[tipoEvento]}</span>
            </label>
          ))}
        </div>
      </div>

      {allGeoEvents.length === 0 ? (
        <div className="mt-5 rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
          No hay ubicaciones georreferenciadas para este viaje.
        </div>
      ) : geoEvents.length === 0 ? (
        <div className="mt-5 rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
          No hay ubicaciones georreferenciadas para los filtros seleccionados.
        </div>
      ) : (
        <div className="mt-5 overflow-hidden rounded-[1.75rem] border border-slate-200">
          <MapContainer
            center={points[0]}
            className="h-[360px] w-full"
            scrollWheelZoom={true}
            zoom={13}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitBounds points={points} />
            {points.length >= 2 ? (
              <Polyline
                pathOptions={{
                  color: "#334155",
                  weight: 4,
                  opacity: 0.7
                }}
                positions={points}
              />
            ) : null}

            {geoEvents.map((evento) => (
              <Marker
                key={evento.id_evento}
                position={[evento.lat, evento.lng]}
                icon={buildNumberedMarkerIcon(evento.sequence, evento.tipo_evento)}
              >
                <Popup>
                  <div className="space-y-2 text-sm text-slate-800">
                    <p className="font-semibold text-brand-700">Punto {evento.sequence}</p>
                    <p className="font-semibold text-slate-950">{eventLabels[evento.tipo_evento]}</p>
                    <p>{evento.ubicacion}</p>
                    <p>{formatDateTime(evento.created_at)}</p>
                    {evento.comentario ? <p>{evento.comentario}</p> : null}
                    {evento.operador?.alias ? <p>Operador: {evento.operador.alias}</p> : null}
                    {evento.trailer ? (
                      <p>
                        Tráiler: {evento.trailer.numero_economico} · {evento.trailer.placas}
                      </p>
                    ) : null}
                    {evento.caja ? (
                      <p>
                        Caja: {evento.caja.numero_economico ?? "Caja sin número"} · {evento.caja.placas}
                      </p>
                    ) : null}
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      )}
    </Card>
  );
}
