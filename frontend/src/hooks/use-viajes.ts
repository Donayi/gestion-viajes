"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/services/api-client";
import { getViajesEnrichedRequest } from "@/services/viajes.service";
import type { ViajeListItem } from "@/types/viaje";

export function useViajes() {
  const [viajes, setViajes] = useState<ViajeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getViajesEnrichedRequest();
      setViajes(data);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "No fue posible cargar los viajes";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { viajes, loading, error, reload: load };
}
