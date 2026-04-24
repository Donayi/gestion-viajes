"use client";

import { OperatorDashboard } from "@/components/dashboard/operator-dashboard";
import { StatCard } from "@/components/dashboard/stat-card";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { useSession } from "@/hooks/use-session";
import { useViajes } from "@/hooks/use-viajes";
import { isOperador } from "@/lib/permissions";

export default function DashboardPage() {
  const { user } = useSession();
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
