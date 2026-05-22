import { StatusBadge } from "@/components/ui/status-badge";

const variantMap: Record<string, Parameters<typeof StatusBadge>[0]["variant"]> = {
  CREADO: "neutral",
  ASIGNADO: "info",
  CARGANDO: "primary",
  INICIADO: "primary",
  RETRASADO: "warning",
  STANDBY: "warning",
  FINALIZADO: "success",
  CANCELADO: "danger"
};

export function ViajeStatusBadge({ clave, nombre }: { clave: string; nombre: string }) {
  return (
    <StatusBadge variant={variantMap[clave] ?? "neutral"}>
      {nombre}
    </StatusBadge>
  );
}
