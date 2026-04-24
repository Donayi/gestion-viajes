import { Card } from "@/components/ui/card";
import { formatDateTime } from "@/lib/formatters";
import type { HistorialEstatusEnriched } from "@/types/viaje";

export function ViajeTimeline({ historial }: { historial: HistorialEstatusEnriched[] }) {
  return (
    <Card className="p-5 md:p-6">
      <h2 className="text-lg font-semibold text-slate-950">Historial de estatus</h2>

      <div className="mt-5 space-y-4">
        {historial.map((item) => (
          <div
            key={item.id_historial}
            className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
          >
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <p className="font-semibold text-slate-900">{item.estatus.nombre}</p>
              <p className="text-sm text-slate-500">{formatDateTime(item.changed_at)}</p>
            </div>
            <p className="mt-2 text-sm text-slate-700">
              {item.comentario ?? "Sin comentario"}
            </p>
            <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-500">
              {item.usuario_cambio
                ? `${item.usuario_cambio.nombre} ${item.usuario_cambio.apellido}`
                : "Sin usuario"}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
