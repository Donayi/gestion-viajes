"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/services/api-client";
import {
  getViajeAsignacionesRequest,
  getViajeDetailRequest,
  getViajeHistorialRequest
} from "@/services/viajes.service";
import type {
  HistorialEstatusEnriched,
  ViajeAsignacionEnriched,
  ViajeDetail
} from "@/types/viaje";

export function useViajeDetail(viajeId: number) {
  const [detail, setDetail] = useState<ViajeDetail | null>(null);
  const [historial, setHistorial] = useState<HistorialEstatusEnriched[]>([]);
  const [asignaciones, setAsignaciones] = useState<ViajeAsignacionEnriched[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [detailData, historialData, asignacionesData] = await Promise.all([
        getViajeDetailRequest(viajeId),
        getViajeHistorialRequest(viajeId),
        getViajeAsignacionesRequest(viajeId)
      ]);

      setDetail(detailData);
      setHistorial(historialData);
      setAsignaciones(asignacionesData);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "No fue posible cargar el detalle del viaje";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [viajeId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { detail, historial, asignaciones, loading, error, reload: load };
}
