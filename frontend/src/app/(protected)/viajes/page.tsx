"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { ViajesMobileList } from "@/components/viajes/viajes-mobile-list";
import { ViajesTable } from "@/components/viajes/viajes-table";
import { useSession } from "@/hooks/use-session";
import { useViajes } from "@/hooks/use-viajes";
import { isAdmin } from "@/lib/permissions";

export default function ViajesPage() {
  const { user } = useSession();
  const { viajes, loading, error, reload } = useViajes();

  if (loading) {
    return <LoadingState label="Cargando viajes..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void reload()} />;
  }

  if (!viajes.length) {
    return (
      <EmptyState
        title="No hay viajes visibles"
        description="Cuando existan viajes disponibles para este usuario, apareceran aqui."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div
        className={
          isAdmin(user)
            ? ""
            : "rounded-[2rem] border border-white/10 bg-white/10 p-5 shadow-soft backdrop-blur"
        }
      >
        <p
          className={`text-xs font-semibold uppercase tracking-[0.22em] ${
            isAdmin(user) ? "text-brand-700" : "text-brand-200"
          }`}
        >
          Operacion diaria
        </p>
        <h2 className={`mt-3 text-3xl font-semibold ${isAdmin(user) ? "text-slate-950" : "text-white"}`}>
          Viajes
        </h2>
        <p className={`mt-2 text-sm ${isAdmin(user) ? "text-slate-600" : "text-slate-300"}`}>
          {isAdmin(user)
            ? "Vista completa de los viajes visibles para administracion."
            : "Tus viajes listos para operar. Abre uno y ejecuta acciones rapidas en campo."}
        </p>
      </div>

      {isAdmin(user) ? (
        <>
          <ViajesMobileList viajes={viajes} user={user} />
          <ViajesTable viajes={viajes} />
        </>
      ) : (
        <ViajesMobileList viajes={viajes} user={user} />
      )}
    </div>
  );
}
