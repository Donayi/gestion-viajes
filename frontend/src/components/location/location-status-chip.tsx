"use client";

import { Button } from "@/components/ui/button";
import { usePersistentLocation } from "@/hooks/use-persistent-location";

function getChipClass(status: string, stale: boolean) {
  if (status === "denied") return "border-red-200 bg-red-50 text-red-700";
  if (status === "unavailable" || status === "error") return "border-amber-200 bg-amber-50 text-amber-800";
  if (status === "requesting") return "border-sky-200 bg-sky-50 text-sky-700";
  if (stale) return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

export function LocationStatusChip() {
  const { enabledForRole, location, refreshLocation, stale, status, statusMessage } = usePersistentLocation();

  if (!enabledForRole) {
    return null;
  }

  return (
    <div className={`rounded-2xl border px-3 py-2 text-xs ${getChipClass(status, stale)}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold">{statusMessage ?? "Ubicación disponible"}</p>
          <p className="mt-1 opacity-80">
            DAFREQ usa tu ubicación sólo para registrar eventos operativos mientras la app está abierta.
          </p>
        </div>
        <Button
          className="shrink-0"
          onClick={refreshLocation}
          size="sm"
          type="button"
          variant={status === "denied" ? "warning" : "ghost"}
        >
          {status === "denied" ? "Reintentar permiso" : "Actualizar ubicación"}
        </Button>
      </div>
      {location ? (
        <p className="mt-2 opacity-70">
          {location.latitud.toFixed(5)}, {location.longitud.toFixed(5)}
          {location.accuracy ? ` · ±${Math.round(location.accuracy)} m` : ""}
        </p>
      ) : null}
    </div>
  );
}
