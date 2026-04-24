import { cn } from "@/lib/cn";

const colorMap: Record<string, string> = {
  CREADO: "bg-slate-100 text-slate-700",
  ASIGNADO: "bg-blue-100 text-blue-700",
  CARGANDO: "bg-amber-100 text-amber-700",
  INICIADO: "bg-emerald-100 text-emerald-700",
  RETRASADO: "bg-red-100 text-red-700",
  STANDBY: "bg-orange-100 text-orange-700",
  FINALIZADO: "bg-emerald-200 text-emerald-900",
  CANCELADO: "bg-slate-200 text-slate-800"
};

export function ViajeStatusBadge({ clave, nombre }: { clave: string; nombre: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]",
        colorMap[clave] ?? "bg-slate-100 text-slate-700"
      )}
    >
      {nombre}
    </span>
  );
}
