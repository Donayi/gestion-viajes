"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { OperatorDashboard } from "@/components/dashboard/operator-dashboard";
import { StatCard } from "@/components/dashboard/stat-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useSession } from "@/hooks/use-session";
import { useViajes } from "@/hooks/use-viajes";
import { isAdmin, isOperador } from "@/lib/permissions";
import { ApiError } from "@/services/api-client";
import { getAdminDashboardRequest } from "@/services/dashboard.service";
import type { CurrentUser } from "@/types/auth";
import type { AdminDashboardResponse } from "@/types/dashboard";

function formatDateTime(value: string) {
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return "Sin fecha disponible";
  }

  return parsedDate.toLocaleString("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

function LegacyDashboardView({ user }: { user: CurrentUser | null }) {
  const { viajes, loading, error, reload } = useViajes();

  if (loading) {
    return <LoadingState label="Cargando dashboard..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void reload()} />;
  }

  const activos = viajes.filter(
    (viaje) => !["FINALIZADO", "CANCELADO"].includes(viaje.estatus_actual.clave)
  ).length;
  const finalizados = viajes.filter(
    (viaje) => viaje.estatus_actual.clave === "FINALIZADO"
  ).length;

  if (isOperador(user)) {
    return <OperatorDashboard user={user} viajes={viajes} />;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
        <StatCard label="Viajes visibles" value={viajes.length} />
        <StatCard label="Viajes activos" value={activos} />
        <StatCard label="Viajes finalizados" value={finalizados} />
        <StatCard
          label="Usuario actual"
          value={`${user?.nombre ?? ""} ${user?.apellido ?? ""}`.trim()}
        />
      </section>

      <Card className="p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
          Sesion actual
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-slate-950">
          {user?.nombre} {user?.apellido}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Usuario: {user?.username} · Rol: {user?.rol}
        </p>
      </Card>
    </div>
  );
}

function AdminDashboardContainer({ user }: { user: CurrentUser | null }) {
  const mountedRef = useRef(true);
  const activeControllerRef = useRef<AbortController | null>(null);
  const latestRequestIdRef = useRef(0);
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      activeControllerRef.current?.abort();
      activeControllerRef.current = null;
    };
  }, []);

  const load = useCallback(async () => {
    activeControllerRef.current?.abort();
    const controller = new AbortController();
    activeControllerRef.current = controller;
    const requestId = latestRequestIdRef.current + 1;
    latestRequestIdRef.current = requestId;

    setLoading(true);
    setError(null);

    try {
      const data = await getAdminDashboardRequest(controller.signal);
      if (
        !mountedRef.current ||
        controller.signal.aborted ||
        latestRequestIdRef.current !== requestId
      ) {
        return;
      }
      setDashboard(data);
    } catch (currentError) {
      if (
        !mountedRef.current ||
        latestRequestIdRef.current !== requestId ||
        isAbortError(currentError)
      ) {
        return;
      }
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible cargar el dashboard administrativo."
      );
    } finally {
      if (activeControllerRef.current === controller) {
        activeControllerRef.current = null;
      }
      if (mountedRef.current && latestRequestIdRef.current === requestId) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <LoadingState label="Cargando dashboard administrativo..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  if (!dashboard) {
    return (
      <Card className="p-6">
        <p className="text-sm text-slate-600">
          No fue posible obtener informacion del dashboard administrativo.
        </p>
        <Button className="mt-4" onClick={() => void load()} type="button">
          Reintentar
        </Button>
      </Card>
    );
  }

  const emptyDashboard =
    dashboard.viajes_resumen.total === 0 &&
    dashboard.alertas.pendientes_total === 0 &&
    dashboard.mantenimientos.abiertos_total === 0;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        <StatCard label="Total de viajes" value={dashboard.viajes_resumen.total} />
        <StatCard label="Viajes activos" value={dashboard.viajes_resumen.activos} />
        <StatCard label="Viajes finalizados" value={dashboard.viajes_resumen.finalizados} />
        <StatCard label="Alertas pendientes" value={dashboard.alertas.pendientes_total} />
        <StatCard label="Mantenimientos abiertos" value={dashboard.mantenimientos.abiertos_total} />
        <StatCard
          label="Operadores disponibles"
          value={dashboard.disponibilidad.operadores.disponibles}
        />
      </section>

      <Card className="p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
          Sesion actual
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-slate-950">
          {user?.nombre} {user?.apellido}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Usuario: {user?.username} · Rol: {user?.rol}
        </p>
        <p className="mt-4 text-sm text-slate-500">
          Ultima actualizacion: {formatDateTime(dashboard.generated_at)}
        </p>
      </Card>

      {emptyDashboard ? (
        <Card className="p-6">
          <p className="text-sm text-slate-600">
            Aun no hay actividad operativa para mostrar en el dashboard administrativo.
          </p>
        </Card>
      ) : null}
    </div>
  );
}

export default function DashboardPage() {
  const { user, status } = useSession();

  if (status === "loading") {
    return <LoadingState label="Cargando sesion..." />;
  }

  if (isAdmin(user)) {
    return <AdminDashboardContainer user={user} />;
  }

  return <LegacyDashboardView user={user} />;
}
