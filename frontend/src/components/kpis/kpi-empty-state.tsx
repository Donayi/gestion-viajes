import { EmptyState } from "@/components/ui/empty-state";

export function KpiEmptyState({
  title = "No hay KPIs operativos para mostrar",
  description = "Ajusta los filtros o registra eventos operativos para empezar a calcular indicadores.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <EmptyState
      description={description}
      title={title}
    />
  );
}
