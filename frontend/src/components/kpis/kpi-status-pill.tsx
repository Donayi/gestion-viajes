import { cn } from "@/lib/cn";

export function KpiStatusPill({
  kpiCompleto,
  kpiValido,
  anomalia
}: {
  kpiCompleto: boolean;
  kpiValido: boolean;
  anomalia: string | null;
}) {
  let label = "Completo";
  let classes = "bg-emerald-50 text-emerald-700 border-emerald-200";

  if (!kpiCompleto) {
    label = anomalia === "EVENTO_INICIO_FALTANTE" ? "Falta inicio" : "Falta final";
    classes = "bg-amber-50 text-amber-700 border-amber-200";
  } else if (!kpiValido) {
    label = anomalia === "KM_FINAL_MENOR_INICIO" ? "KM inválido" : "Diésel inválido";
    classes = "bg-red-50 text-red-700 border-red-200";
  }

  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-3 py-1 text-xs font-semibold",
        classes
      )}
      title={anomalia ?? undefined}
    >
      {label}
    </span>
  );
}
