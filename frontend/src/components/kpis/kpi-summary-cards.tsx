import { Card } from "@/components/ui/card";
import type { KpiOperativoResumen } from "@/types/kpi";

const cards = [
  { key: "total_viajes_con_eventos", label: "Viajes con eventos" },
  { key: "km_total_recorridos", label: "KM totales" },
  { key: "km_promedio_por_viaje", label: "KM promedio" },
  { key: "diesel_total_consumido_estimado", label: "Diésel total" },
  { key: "diesel_promedio_consumido", label: "Diésel promedio" },
  { key: "numero_total_standbys", label: "Standbys" },
  { key: "viajes_finalizados_con_kpi", label: "KPIs completos" }
] as const;

export function KpiSummaryCards({ resumen }: { resumen: KpiOperativoResumen }) {
  return (
    <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
      {cards.map((card) => (
        <Card
          key={card.key}
          className="border-brand-100 bg-gradient-to-br from-brand-50 via-white to-slate-50 p-5"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
            {card.label}
          </p>
          <p className="mt-4 text-3xl font-semibold text-slate-950">
            {formatKpiValue(card.key, resumen[card.key])}
          </p>
        </Card>
      ))}
    </section>
  );
}

function formatKpiValue(key: keyof KpiOperativoResumen, value: number) {
  if (key.includes("km") || key.includes("diesel")) {
    return value.toLocaleString("es-MX", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    });
  }

  return value.toLocaleString("es-MX");
}
