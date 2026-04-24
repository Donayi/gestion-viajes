import { Card } from "@/components/ui/card";
import { ViajeAsignaciones } from "@/components/viajes/viaje-asignaciones";
import { ViajeTimeline } from "@/components/viajes/viaje-timeline";
import { MobileStatusHeader } from "@/components/viajes/mobile-status-header";
import { OperatorActionPanel } from "@/components/viajes/operator-action-panel";
import type {
  HistorialEstatusEnriched,
  ViajeAsignacionEnriched,
  ViajeDetail
} from "@/types/viaje";

function ResourceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-900">{value}</p>
    </div>
  );
}

export function OperatorTripDetail({
  detail,
  historial,
  asignaciones,
  onSuccess
}: {
  detail: ViajeDetail;
  historial: HistorialEstatusEnriched[];
  asignaciones: ViajeAsignacionEnriched[];
  onSuccess: () => Promise<void>;
}) {
  return (
    <div className="space-y-5">
      <MobileStatusHeader viaje={detail} />

      <Card className="rounded-[2rem] p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">Ruta</p>
        <div className="mt-5 flex gap-4">
          <div className="flex flex-col items-center">
            <span className="h-3 w-3 rounded-full bg-brand-600" />
            <span className="h-16 w-px bg-brand-200" />
            <span className="h-3 w-3 rounded-full bg-slate-900" />
          </div>
          <div className="space-y-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Origen</p>
              <p className="mt-1 text-base font-semibold text-slate-900">{detail.lugar_inicio}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Destino</p>
              <p className="mt-1 text-base font-semibold text-slate-900">{detail.lugar_destino}</p>
            </div>
          </div>
        </div>
        <div className="mt-5 rounded-[1.5rem] bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Cliente</p>
          <p className="mt-1 text-sm font-medium text-slate-900">{detail.cliente.nombre_razon_social}</p>
        </div>
      </Card>

      <Card className="rounded-[2rem] p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">Recursos</p>
        <div className="mt-4 grid gap-3">
          <ResourceItem label="Operador" value={detail.operador_actual?.alias ?? "Sin asignar"} />
          <ResourceItem label="Trailer" value={detail.trailer_actual?.numero_economico ?? "Sin asignar"} />
          <ResourceItem
            label="Caja"
            value={detail.caja_actual?.numero_economico ?? detail.caja_actual?.placas ?? "Sin asignar"}
          />
        </div>
      </Card>

      <OperatorActionPanel onSuccess={onSuccess} viaje={detail} />
      <ViajeTimeline historial={historial} />
      <ViajeAsignaciones asignaciones={asignaciones} />
    </div>
  );
}
