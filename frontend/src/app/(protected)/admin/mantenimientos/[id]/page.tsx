import { MantenimientosWorkbench } from "@/app/(protected)/admin/mantenimientos/page";

export default async function AdminMantenimientoDetallePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const parsedId = Number(id);

  return (
    <MantenimientosWorkbench
      variant="admin"
      focusMaintenanceId={Number.isFinite(parsedId) ? parsedId : null}
      maintenanceView="detail"
    />
  );
}
