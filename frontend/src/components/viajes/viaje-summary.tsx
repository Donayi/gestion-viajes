import { Card } from "@/components/ui/card";
import { formatDate, formatDateTime } from "@/lib/formatters";
import type { ViajeDetail } from "@/types/viaje";

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="text-sm text-slate-800">{value}</p>
    </div>
  );
}

export function ViajeSummary({ viaje }: { viaje: ViajeDetail }) {
  return (
    <Card className="p-5 md:p-6">
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <Item label="Cliente" value={viaje.cliente.nombre_razon_social} />
        <Item label="Origen" value={viaje.lugar_inicio} />
        <Item label="Destino" value={viaje.lugar_destino} />
        <Item label="Tipo de carga" value={viaje.tipo_carga ?? "Sin dato"} />
        <Item label="Descripcion" value={viaje.descripcion_carga ?? "Sin dato"} />
        <Item label="Salida programada" value={formatDateTime(viaje.fecha_programada_salida)} />
        <Item label="Fecha de inicio" value={formatDateTime(viaje.fecha_inicio)} />
        <Item label="Fecha de llegada" value={formatDateTime(viaje.fecha_llegada)} />
        <Item label="Fecha de entrega" value={formatDate(viaje.fecha_entrega)} />
        <Item label="Operador actual" value={viaje.operador_actual?.alias ?? "Sin asignar"} />
        <Item
          label="Trailer actual"
          value={viaje.trailer_actual?.numero_economico ?? "Sin asignar"}
        />
        <Item
          label="Caja actual"
          value={viaje.caja_actual?.numero_economico ?? viaje.caja_actual?.placas ?? "Sin asignar"}
        />
      </div>

      <div className="mt-6 rounded-2xl bg-slate-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          Observaciones
        </p>
        <p className="mt-2 text-sm text-slate-700">{viaje.observaciones ?? "Sin observaciones"}</p>
      </div>
    </Card>
  );
}
