import { Card } from "@/components/ui/card";
import { formatDateTime } from "@/lib/formatters";
import type { ViajeAsignacionEnriched } from "@/types/viaje";

export function ViajeAsignaciones({ asignaciones }: { asignaciones: ViajeAsignacionEnriched[] }) {
  return (
    <Card className="p-5 md:p-6">
      <h2 className="text-lg font-semibold text-slate-950">Asignaciones</h2>

      <div className="mt-5 space-y-4">
        {asignaciones.map((asignacion) => (
          <div
            key={asignacion.id_asignacion}
            className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
          >
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <p className="text-sm font-semibold text-slate-900">
                {asignacion.operador?.alias ?? "Sin operador"} ·{" "}
                {asignacion.trailer?.numero_economico ?? "Sin trailer"}
              </p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                {asignacion.activo ? "Activa" : "Cerrada"}
              </p>
            </div>
            <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
              <p>Caja: {asignacion.caja?.numero_economico ?? asignacion.caja?.placas ?? "Sin caja"}</p>
              <p>Fecha: {formatDateTime(asignacion.fecha_asignacion)}</p>
              <p>Motivo: {asignacion.motivo ?? "Sin motivo"}</p>
              <p>Comentario: {asignacion.comentario ?? "Sin comentario"}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
