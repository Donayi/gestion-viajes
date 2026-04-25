import { EmptyState } from "@/components/ui/empty-state";

export function KpiEmptyState() {
  return (
    <EmptyState
      description="Ajusta los filtros o registra eventos operativos para empezar a calcular indicadores."
      title="No hay KPIs operativos para mostrar"
    />
  );
}
