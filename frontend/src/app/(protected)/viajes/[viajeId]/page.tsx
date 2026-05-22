"use client";

import { useParams } from "next/navigation";

import { OperatorTripDetail } from "@/components/viajes/operator-trip-detail";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Card } from "@/components/ui/card";
import { ViajeAsignaciones } from "@/components/viajes/viaje-asignaciones";
import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import { ViajeSummary } from "@/components/viajes/viaje-summary";
import { ViajeTimeline } from "@/components/viajes/viaje-timeline";
import { ViajeEventosOperativos } from "@/components/viajes/viaje-eventos-operativos";
import { ViajeEventosMap } from "@/components/viajes/viaje-eventos-map";
import { ViajeRouteMap } from "@/components/viajes/viaje-route-map";
import { WorkflowActions } from "@/components/viajes/workflow-actions";
import { getPendingStandbyRequest } from "@/components/viajes/workflow-helpers";
import { useSession } from "@/hooks/use-session";
import { useViajeDetail } from "@/hooks/use-viaje-detail";
import { isAdmin, isOperador } from "@/lib/permissions";
import Link from "next/link";

export default function ViajeDetailPage() {
  const { user } = useSession();
  const params = useParams<{ viajeId: string }>();
  const viajeId = Number(params.viajeId);
  const { detail, historial, asignaciones, loading, error, reload } = useViajeDetail(viajeId);

  if (loading) {
    return <LoadingState label="Cargando detalle del viaje..." />;
  }

  if (error || !detail) {
    return (
      <ErrorState
        message={error ?? "No fue posible cargar el viaje"}
        onRetry={() => void reload()}
      />
    );
  }

  if (isOperador(user)) {
    return (
      <OperatorTripDetail
        asignaciones={asignaciones}
        detail={detail}
        historial={historial}
        onSuccess={reload}
      />
    );
  }

  const hasPendingStandbyRequest = getPendingStandbyRequest(detail) !== null;

  const assignmentCtaLabel =
    detail.estatus_actual.clave === "STANDBY"
      ? "Reasignar viaje"
      : detail.estatus_actual.clave === "ASIGNADO"
        ? "Reasignar viaje"
      : !detail.id_operador_actual && !detail.id_trailer_actual
        ? "Asignar viaje"
        : "Editar viaje";
  const isFinalizado = detail.estatus_actual.clave === "FINALIZADO";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <Link className="text-sm font-medium text-brand-700" href="/viajes">
            ← Volver a viajes
          </Link>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h2 className="text-3xl font-semibold text-slate-950">{detail.folio}</h2>
            <ViajeStatusBadge
              clave={detail.estatus_actual.clave}
              nombre={detail.estatus_actual.nombre}
            />
          </div>
          <p className="mt-2 text-sm text-slate-600">{detail.cliente.nombre_razon_social}</p>
          {hasPendingStandbyRequest ? (
            <p className="mt-2 text-sm font-medium text-amber-700">
              El operador solicitó poner este viaje en standby.
            </p>
          ) : null}
        </div>
        {isAdmin(user) && !isFinalizado ? (
          <div className="flex flex-wrap gap-3">
            <Link
              className="inline-flex items-center justify-center rounded-2xl bg-brand-700 px-4 py-3 text-sm font-medium text-white"
              href={`/admin/viajes/${detail.id_viaje}/editar`}
            >
              {assignmentCtaLabel}
            </Link>
          </div>
        ) : null}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          {detail.estatus_actual.clave === "STANDBY" ? (
            <Card className="border-amber-200 bg-amber-50 p-5 md:p-6">
              <h2 className="text-lg font-semibold text-amber-950">
                Viaje en standby, pendiente de reasignación administrativa.
              </h2>
              <p className="mt-2 text-sm text-amber-800">
                El operador ya no puede retomarlo por su cuenta. Debe reasignarse desde administración.
              </p>
            </Card>
          ) : null}
          {isFinalizado ? (
            <Card className="border-emerald-200 bg-emerald-50 p-5 md:p-6">
              <h2 className="text-lg font-semibold text-emerald-950">
                Viaje finalizado
              </h2>
              <p className="mt-2 text-sm text-emerald-800">
                Este viaje quedó cerrado definitivamente. Solo está disponible para consulta de detalle,
                historial, evidencias y eventos operativos.
              </p>
            </Card>
          ) : null}
          <ViajeSummary viaje={detail} />
          <ViajeRouteMap
            destino={{
              direccion: detail.lugar_destino,
              latitud: detail.lugar_destino_latitud,
              longitud: detail.lugar_destino_longitud,
            }}
            origen={{
              direccion: detail.lugar_inicio,
              latitud: detail.lugar_inicio_latitud,
              longitud: detail.lugar_inicio_longitud,
            }}
          />
          <div id="eventos-operativos">
            <ViajeEventosOperativos eventos={detail.eventos_operativos} onCorrected={reload} viajeId={detail.id_viaje} />
          </div>
          {isAdmin(user) ? <ViajeEventosMap eventos={detail.eventos_operativos} /> : null}
          <ViajeTimeline historial={historial} />
          <ViajeAsignaciones asignaciones={asignaciones} />
        </div>

        <div className="space-y-6">
          <WorkflowActions onSuccess={reload} viaje={detail} />
          <Card className="p-5 md:p-6">
            <h2 className="text-lg font-semibold text-slate-950">Recursos actuales</h2>
            <div className="mt-5 space-y-3 text-sm text-slate-700">
              <p>Operador: {detail.operador_actual?.alias ?? "Sin asignar"}</p>
              <p>Trailer: {detail.trailer_actual?.numero_economico ?? "Sin asignar"}</p>
              <p>
                Caja: {detail.caja_actual?.numero_economico ?? detail.caja_actual?.placas ?? "Sin asignar"}
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
