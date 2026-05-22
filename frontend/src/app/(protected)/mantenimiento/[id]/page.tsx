import { MaintenanceGuard } from "@/components/auth/maintenance-guard";
import { MantenimientosWorkbench } from "@/app/(protected)/admin/mantenimientos/page";

export default async function MantenimientoDetallePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const parsedId = Number(id);

  return (
    <MaintenanceGuard>
      <MantenimientosWorkbench
        variant="maintenance"
        focusMaintenanceId={Number.isFinite(parsedId) ? parsedId : null}
        maintenanceView="detail"
      />
    </MaintenanceGuard>
  );
}
