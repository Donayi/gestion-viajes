"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AdminDashboard } from "@/components/dashboard/admin-dashboard";
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
  const dashboardRef = useRef<AdminDashboardResponse | null>(null);
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
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
    const hasCurrentDashboard = dashboardRef.current !== null;

    setRefreshing(true);
    if (!hasCurrentDashboard) {
      setInitialLoading(true);
    }
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
      dashboardRef.current = data;
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
        setRefreshing(false);
        if (!hasCurrentDashboard) {
          setInitialLoading(false);
        }
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (initialLoading && !dashboard) {
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

  return (
    <AdminDashboard
      dashboard={dashboard}
      onRefresh={() => void load()}
      refreshing={refreshing}
      user={user}
    />
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
