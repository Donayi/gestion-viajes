"use client";

import { useEffect, useMemo, useState } from "react";
import { divIcon } from "leaflet";
import type { LatLngTuple } from "leaflet";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const DEFAULT_CENTER: LatLngTuple = [25.6866, -100.3161];

type LocationPickerClientProps = {
  label: string;
  address: string;
  latitude: number | string | null;
  longitude: number | string | null;
  onAddressChange: (value: string) => void;
  onCoordinatesChange: (coords: { latitud: number | null; longitud: number | null }) => void;
};

type GeocodeResult = {
  lat: string;
  lon: string;
  display_name: string;
};

function normalizeCoordinate(value: number | string | null): number | null {
  if (value === null || value === "") {
    return null;
  }

  const normalized = typeof value === "number" ? value : Number(value);
  return Number.isFinite(normalized) ? normalized : null;
}

function buildPinIcon(label: string) {
  return divIcon({
    className: "location-picker-marker-wrapper",
    html: `
      <div style="
        display:flex;
        align-items:center;
        justify-content:center;
        min-width:2.25rem;
        height:2.25rem;
        padding:0 0.5rem;
        border-radius:9999px;
        background:#0f172a;
        color:#ffffff;
        border:2px solid #3b82f6;
        box-shadow:0 10px 24px rgba(15,23,42,0.18);
        font-size:0.75rem;
        font-weight:700;
      ">${label}</div>
    `,
    iconSize: [42, 36],
    iconAnchor: [21, 18],
  });
}

function RecenterMap({ center }: { center: LatLngTuple }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);

  return null;
}

function MapClickHandler({
  onPick,
}: {
  onPick: (position: LatLngTuple) => void;
}) {
  useMapEvents({
    click(event) {
      onPick([event.latlng.lat, event.latlng.lng]);
    },
  });

  return null;
}

export function LocationPickerClient({
  label,
  address,
  latitude,
  longitude,
  onAddressChange,
  onCoordinatesChange,
}: LocationPickerClientProps) {
  const normalizedLatitude = normalizeCoordinate(latitude);
  const normalizedLongitude = normalizeCoordinate(longitude);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [mapCenter, setMapCenter] = useState<LatLngTuple>(
    normalizedLatitude !== null && normalizedLongitude !== null
      ? [normalizedLatitude, normalizedLongitude]
      : DEFAULT_CENTER
  );

  const markerPosition = useMemo<LatLngTuple | null>(() => {
    if (normalizedLatitude === null || normalizedLongitude === null) {
      return null;
    }
    return [normalizedLatitude, normalizedLongitude];
  }, [normalizedLatitude, normalizedLongitude]);

  useEffect(() => {
    if (markerPosition) {
      setMapCenter(markerPosition);
    }
  }, [markerPosition]);

  async function handleSearch() {
    if (!address.trim()) {
      setSearchError("Escribe una dirección o referencia antes de buscar en el mapa.");
      return;
    }

    setSearching(true);
    setSearchError(null);

    try {
      const params = new URLSearchParams({
        q: address.trim(),
        format: "json",
        limit: "1",
      });

      const response = await fetch(`https://nominatim.openstreetmap.org/search?${params.toString()}`, {
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("No fue posible consultar el proveedor de geocodificación.");
      }

      const results = (await response.json()) as GeocodeResult[];
      const firstResult = results[0];

      if (!firstResult) {
        setSearchError("No se encontraron resultados para esa dirección.");
        return;
      }

      const latitud = Number(firstResult.lat);
      const longitud = Number(firstResult.lon);

      if (Number.isNaN(latitud) || Number.isNaN(longitud)) {
        throw new Error("La búsqueda devolvió coordenadas inválidas.");
      }

      onCoordinatesChange({ latitud, longitud });
      onAddressChange(firstResult.display_name || address);
      setMapCenter([latitud, longitud]);
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "No fue posible buscar la dirección.");
    } finally {
      setSearching(false);
    }
  }

  function handlePointSelection(position: LatLngTuple) {
    onCoordinatesChange({
      latitud: position[0],
      longitud: position[1],
    });
    setMapCenter(position);
    setSearchError(null);
  }

  return (
    <div className="space-y-4 rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <Input
          label={label}
          onChange={(event) => onAddressChange(event.target.value)}
          placeholder="Escribe una dirección o referencia operativa"
          value={address}
        />
        <Button disabled={searching} onClick={() => void handleSearch()} type="button" variant="secondary">
          {searching ? "Buscando..." : "Buscar en mapa"}
        </Button>
      </div>

      <div className="rounded-[1.5rem] border border-slate-200 overflow-hidden">
        <MapContainer center={mapCenter} className="h-[280px] w-full" scrollWheelZoom={true} zoom={13}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <RecenterMap center={mapCenter} />
          <MapClickHandler onPick={handlePointSelection} />
          {markerPosition ? (
            <Marker
              draggable={true}
              eventHandlers={{
                dragend: (event) => {
                  const latlng = event.target.getLatLng();
                  handlePointSelection([latlng.lat, latlng.lng]);
                },
              }}
              icon={buildPinIcon(label.includes("inicio") ? "Inicio" : "Destino")}
              position={markerPosition}
            />
          ) : null}
        </MapContainer>
      </div>

      <div className="flex flex-wrap gap-3 text-sm text-slate-600">
        <span>Haz clic en el mapa para colocar o mover el pin.</span>
        {normalizedLatitude !== null && normalizedLongitude !== null ? (
          <span className="font-medium text-slate-800">
            Lat: {normalizedLatitude.toFixed(6)} · Lng: {normalizedLongitude.toFixed(6)}
          </span>
        ) : (
          <span>Aún no hay coordenadas seleccionadas.</span>
        )}
      </div>

      {searchError ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {searchError}
        </div>
      ) : null}
    </div>
  );
}
