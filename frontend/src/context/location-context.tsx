"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useSession } from "@/hooks/use-session";
import { isMantenimiento, isOperador } from "@/lib/permissions";
import type { PersistentLocationSnapshot, PersistentLocationState } from "@/types/location";

const STORAGE_KEY = "dafreq_last_location";
const STALE_MS = 10 * 60 * 1000;

type LocationContextValue = PersistentLocationState & {
  refreshLocation: () => void;
};

export const LocationContext = createContext<LocationContextValue | null>(null);

function readStoredLocation(): PersistentLocationSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as PersistentLocationSnapshot;
    if (
      typeof parsed.latitud !== "number" ||
      typeof parsed.longitud !== "number" ||
      typeof parsed.timestamp !== "number"
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeStoredLocation(location: PersistentLocationSnapshot | null) {
  if (typeof window === "undefined") {
    return;
  }

  if (!location) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(location));
}

function getStatusMessage(
  status: PersistentLocationState["status"],
  stale: boolean,
  location: PersistentLocationSnapshot | null
) {
  if (status === "requesting") {
    return "Obteniendo ubicación";
  }
  if (status === "denied") {
    return "Ubicación denegada";
  }
  if (status === "unavailable") {
    return "GPS no disponible";
  }
  if (status === "error") {
    return "Error de ubicación";
  }
  if (status === "active" && location) {
    const minutes = Math.max(0, Math.floor((Date.now() - location.timestamp) / 60000));
    return stale ? `Última ubicación hace ${minutes} min` : "GPS activo";
  }
  return null;
}

export function LocationProvider({ children }: { children: ReactNode }) {
  const { user, status } = useSession();
  const enabledForRole = status === "authenticated" && (isOperador(user) || isMantenimiento(user));
  const [location, setLocation] = useState<PersistentLocationSnapshot | null>(null);
  const [locationStatus, setLocationStatus] = useState<PersistentLocationState["status"]>("idle");
  const [stale, setStale] = useState(false);
  const watchIdRef = useRef<number | null>(null);

  const updateLocation = useCallback((nextLocation: PersistentLocationSnapshot) => {
    setLocation(nextLocation);
    setLocationStatus("active");
    setStale(Date.now() - nextLocation.timestamp > STALE_MS);
    writeStoredLocation(nextLocation);
  }, []);

  const refreshLocation = useCallback(() => {
    if (typeof window === "undefined" || !enabledForRole) {
      return;
    }

    if (!navigator.geolocation) {
      setLocationStatus("unavailable");
      return;
    }

    setLocationStatus("requesting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        updateLocation({
          latitud: Number(position.coords.latitude.toFixed(7)),
          longitud: Number(position.coords.longitude.toFixed(7)),
          accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null,
          timestamp: position.timestamp,
        });
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          setLocationStatus("denied");
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          setLocationStatus("unavailable");
        } else {
          setLocationStatus("error");
        }
      },
      {
        enableHighAccuracy: false,
        timeout: 15000,
        maximumAge: 120000,
      }
    );
  }, [enabledForRole, updateLocation]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const stored = readStoredLocation();
    if (stored) {
      setLocation(stored);
      setLocationStatus("active");
      setStale(Date.now() - stored.timestamp > STALE_MS);
    }
  }, []);

  useEffect(() => {
    if (!enabledForRole || typeof window === "undefined") {
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      setLocationStatus("idle");
      return;
    }

    if (!navigator.geolocation) {
      setLocationStatus("unavailable");
      return;
    }

    setLocationStatus((current) => (location ? current : "requesting"));

    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        updateLocation({
          latitud: Number(position.coords.latitude.toFixed(7)),
          longitud: Number(position.coords.longitude.toFixed(7)),
          accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null,
          timestamp: position.timestamp,
        });
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          setLocationStatus("denied");
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          setLocationStatus("unavailable");
        } else {
          setLocationStatus("error");
        }
      },
      {
        enableHighAccuracy: false,
        timeout: 15000,
        maximumAge: 120000,
      }
    );

    return () => {
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, [enabledForRole, updateLocation]);

  useEffect(() => {
    if (!location) {
      setStale(false);
      return;
    }

    const interval = window.setInterval(() => {
      const isStale = Date.now() - location.timestamp > STALE_MS;
      setStale(isStale);
      if (enabledForRole && isStale) {
        refreshLocation();
      }
    }, 60000);

    return () => window.clearInterval(interval);
  }, [enabledForRole, location, refreshLocation]);

  const value = useMemo<LocationContextValue>(
    () => ({
      status: locationStatus,
      location,
      stale,
      enabledForRole,
      statusMessage: getStatusMessage(locationStatus, stale, location),
      refreshLocation,
    }),
    [enabledForRole, location, locationStatus, refreshLocation, stale]
  );

  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}
