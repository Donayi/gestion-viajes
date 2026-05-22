"use client";

import { divIcon } from "leaflet";
import type { LatLngBoundsExpression, LatLngTuple } from "leaflet";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo } from "react";

import { Card } from "@/components/ui/card";

const DEFAULT_CENTER: LatLngTuple = [25.6866, -100.3161];

type PointData = {
  label: "Inicio" | "Destino";
  direccion: string;
  latitud: number | string | null;
  longitud: number | string | null;
};

function normalizeCoordinate(value: number | string | null): number | null {
  if (value === null || value === "") {
    return null;
  }

  const normalized = typeof value === "number" ? value : Number(value);
  return Number.isFinite(normalized) ? normalized : null;
}

function buildMarkerIcon(label: "Inicio" | "Destino") {
  const styles =
    label === "Inicio"
      ? { fill: "#2563eb", border: "#1d4ed8" }
      : { fill: "#0f172a", border: "#334155" };

  return divIcon({
    className: "viaje-route-marker-wrapper",
    html: `
      <div style="
        min-width:3.25rem;
        height:2rem;
        padding:0 0.65rem;
        border-radius:9999px;
        background:${styles.fill};
        color:#ffffff;
        border:2px solid ${styles.border};
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:0.75rem;
        font-weight:700;
        box-shadow:0 10px 24px rgba(15,23,42,0.18);
      ">${label}</div>
    `,
    iconSize: [54, 32],
    iconAnchor: [27, 16],
    popupAnchor: [0, -18],
  });
}

function FitBounds({ points }: { points: LatLngTuple[] }) {
  const map = useMap();

  useEffect(() => {
    if (points.length === 0) {
      map.setView(DEFAULT_CENTER, 11);
      return;
    }

    if (points.length === 1) {
      map.setView(points[0], 13);
      return;
    }

    const bounds: LatLngBoundsExpression = points;
    map.fitBounds(bounds, { padding: [32, 32] });
  }, [map, points]);

  return null;
}

function buildGoogleMapsUrl(point: PointData) {
  const latitud = normalizeCoordinate(point.latitud);
  const longitud = normalizeCoordinate(point.longitud);

  if (latitud !== null && longitud !== null) {
    return `https://www.google.com/maps/search/?api=1&query=${latitud},${longitud}`;
  }

  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(point.direccion)}`;
}

function buildWazeUrl(point: PointData) {
  const latitud = normalizeCoordinate(point.latitud);
  const longitud = normalizeCoordinate(point.longitud);

  if (latitud === null || longitud === null) {
    return null;
  }

  return `https://waze.com/ul?ll=${latitud},${longitud}&navigate=yes`;
}

function GoogleMapsGlyph() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M12 3.25C8.825 3.25 6.25 5.825 6.25 9C6.25 13.125 12 20.75 12 20.75C12 20.75 17.75 13.125 17.75 9C17.75 5.825 15.175 3.25 12 3.25Z"
        fill="#EA4335"
      />
      <path
        d="M12 3.25C8.825 3.25 6.25 5.825 6.25 9C6.25 9.9 6.524 10.914 6.994 11.972L12 6.967L14.876 9.843L9.855 14.864C10.977 16.571 12 17.95 12 17.95C12 17.95 17.75 13.125 17.75 9C17.75 5.825 15.175 3.25 12 3.25Z"
        fill="#4285F4"
        opacity="0.92"
      />
      <path
        d="M12 3.25C10.556 3.25 9.235 3.782 8.223 4.662L11.4 7.839L8.448 10.79L6.489 8.831C6.333 9.487 6.25 10.198 6.25 10.95C6.25 14.575 12 20.75 12 20.75C12 20.75 13.163 19.206 14.498 17.16L10.951 13.613L13.902 10.661L15.88 12.639C17.073 10.64 17.75 8.716 17.75 7.95C17.75 5.825 15.175 3.25 12 3.25Z"
        fill="#34A853"
        opacity="0.95"
      />
      <circle cx="12" cy="9" r="2.45" fill="#FBBC05" />
    </svg>
  );
}

function WazeGlyph() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M12 4.25C7.996 4.25 4.75 7.288 4.75 11.038C4.75 13.363 5.997 15.417 7.91 16.646C8.196 16.83 8.35 17.154 8.327 17.493L8.25 18.625L9.755 17.827C10.004 17.695 10.298 17.67 10.566 17.758C11.026 17.91 11.521 17.993 12.035 17.993H12.25C16.254 17.993 19.5 14.955 19.5 11.205C19.5 7.455 16.254 4.25 12.25 4.25H12Z"
        fill="#33CCFF"
        stroke="#0F172A"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <circle cx="9.15" cy="10.4" r="1.1" fill="white" />
      <circle cx="14.45" cy="10.4" r="1.1" fill="white" />
      <circle cx="9.15" cy="10.4" r="0.38" fill="#0F172A" />
      <circle cx="14.45" cy="10.4" r="0.38" fill="#0F172A" />
      <path
        d="M9.2 13.5C10.05 14.45 11.15 14.9 12.35 14.9C13.55 14.9 14.65 14.45 15.5 13.5"
        stroke="#0F172A"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <circle cx="8.1" cy="17.9" r="1.25" fill="white" stroke="#0F172A" strokeWidth="1" />
      <circle cx="15.9" cy="17.9" r="1.25" fill="white" stroke="#0F172A" strokeWidth="1" />
    </svg>
  );
}

function NavigationLinks({ point }: { point: PointData }) {
  const wazeUrl = buildWazeUrl(point);
  const pointLabel = point.label.toLowerCase();

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      <a
        aria-label={`Abrir ${pointLabel} en Google Maps`}
        className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-200"
        href={buildGoogleMapsUrl(point)}
        rel="noopener noreferrer"
        target="_blank"
        title={`Abrir ${pointLabel} en Google Maps`}
      >
        <GoogleMapsGlyph />
        <span className="hidden sm:inline">Google Maps</span>
        <span className="sr-only">Abrir {pointLabel} en Google Maps</span>
      </a>
      {wazeUrl ? (
        <a
          aria-label={`Abrir ${pointLabel} en Waze`}
          className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-200"
          href={wazeUrl}
          rel="noopener noreferrer"
          target="_blank"
          title={`Abrir ${pointLabel} en Waze`}
        >
          <WazeGlyph />
          <span className="hidden sm:inline">Waze</span>
          <span className="sr-only">Abrir {pointLabel} en Waze</span>
        </a>
      ) : null}
    </div>
  );
}

export function ViajeRouteMapClient({
  origen,
  destino,
}: {
  origen: PointData;
  destino: PointData;
}) {
  const origenLatitud = normalizeCoordinate(origen.latitud);
  const origenLongitud = normalizeCoordinate(origen.longitud);
  const destinoLatitud = normalizeCoordinate(destino.latitud);
  const destinoLongitud = normalizeCoordinate(destino.longitud);

  const points = useMemo(
    () =>
      [
        origenLatitud !== null && origenLongitud !== null
          ? ([origenLatitud, origenLongitud] as LatLngTuple)
          : null,
        destinoLatitud !== null && destinoLongitud !== null
          ? ([destinoLatitud, destinoLongitud] as LatLngTuple)
          : null,
      ].filter((point): point is LatLngTuple => point !== null),
    [destinoLatitud, destinoLongitud, origenLatitud, origenLongitud]
  );

  return (
    <Card className="p-5 md:p-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
          Ubicaciones del viaje
        </p>
        <h2 className="mt-2 text-lg font-semibold text-slate-950">Origen y destino georreferenciados</h2>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Inicio</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{origen.direccion}</p>
          {origenLatitud !== null && origenLongitud !== null ? (
            <p className="mt-2 text-xs text-slate-500">
              {origenLatitud.toFixed(6)}, {origenLongitud.toFixed(6)}
            </p>
          ) : (
            <p className="mt-2 text-xs text-slate-500">Sin coordenadas registradas.</p>
          )}
          <NavigationLinks point={origen} />
        </div>

        <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Destino</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{destino.direccion}</p>
          {destinoLatitud !== null && destinoLongitud !== null ? (
            <p className="mt-2 text-xs text-slate-500">
              {destinoLatitud.toFixed(6)}, {destinoLongitud.toFixed(6)}
            </p>
          ) : (
            <p className="mt-2 text-xs text-slate-500">Sin coordenadas registradas.</p>
          )}
          <NavigationLinks point={destino} />
        </div>
      </div>

      {points.length === 0 ? (
        <div className="mt-5 rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
          Este viaje aún no tiene ubicación georreferenciada.
        </div>
      ) : (
        <div className="mt-5 overflow-hidden rounded-[1.75rem] border border-slate-200">
          <MapContainer center={points[0] ?? DEFAULT_CENTER} className="h-[320px] w-full" scrollWheelZoom={true} zoom={12}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitBounds points={points} />
            {points.length >= 2 ? (
              <Polyline
                pathOptions={{ color: "#334155", weight: 4, opacity: 0.75 }}
                positions={points}
              />
            ) : null}
            {origenLatitud !== null && origenLongitud !== null ? (
              <Marker
                icon={buildMarkerIcon("Inicio")}
                position={[origenLatitud, origenLongitud]}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-semibold text-slate-900">Inicio</p>
                    <p className="mt-1 text-slate-700">{origen.direccion}</p>
                  </div>
                </Popup>
              </Marker>
            ) : null}
            {destinoLatitud !== null && destinoLongitud !== null ? (
              <Marker
                icon={buildMarkerIcon("Destino")}
                position={[destinoLatitud, destinoLongitud]}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-semibold text-slate-900">Destino</p>
                    <p className="mt-1 text-slate-700">{destino.direccion}</p>
                  </div>
                </Popup>
              </Marker>
            ) : null}
          </MapContainer>
        </div>
      )}
    </Card>
  );
}
