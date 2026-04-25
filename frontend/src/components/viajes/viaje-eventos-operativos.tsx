import { Card } from "@/components/ui/card";
import { formatDateTime } from "@/lib/formatters";
import type { EventoOperativoViaje } from "@/types/viaje";

const eventLabels: Record<EventoOperativoViaje["tipo_evento"], string> = {
  INICIO_VIAJE: "Inicio de viaje",
  STANDBY: "Standby",
  FINALIZACION_VIAJE: "Finalización"
};

export function ViajeEventosOperativos({
  eventos
}: {
  eventos: EventoOperativoViaje[];
}) {
  return (
    <Card className="p-5 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
            KPIs de campo
          </p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950">Eventos operativos</h2>
        </div>
        <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
          {eventos.length}
        </span>
      </div>

      {eventos.length === 0 ? (
        <div className="mt-5 rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
          Aún no hay capturas operativas para este viaje.
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {eventos.map((evento) => (
            <div
              key={evento.id_evento}
              className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-950">
                    {eventLabels[evento.tipo_evento]}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{formatDateTime(evento.created_at)}</p>
                </div>
                <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                  #{evento.id_evento}
                </span>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Metric label="Kilometraje" value={`${evento.kilometraje} km`} />
                <Metric label="Diésel" value={`${evento.nivel_diesel}%`} />
                <Metric label="Ubicación" value={evento.ubicacion} />
                <Metric
                  label="Coordenadas"
                  value={
                    evento.latitud !== null && evento.longitud !== null
                      ? `${evento.latitud}, ${evento.longitud}`
                      : "Sin geolocalización"
                  }
                />
              </div>

              {evento.comentario ? (
                <div className="mt-4 rounded-[1.25rem] bg-white px-3 py-3 text-sm text-slate-700">
                  {evento.comentario}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] bg-white px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-900">{value}</p>
    </div>
  );
}
