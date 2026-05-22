import { MaintenanceGuard } from "@/components/auth/maintenance-guard";
import { MantenimientosWorkbench } from "@/app/(protected)/admin/mantenimientos/page";

export default function MantenimientoNuevoPage() {
  return (
    <MaintenanceGuard>
      <MantenimientosWorkbench variant="maintenance" startCreate maintenanceView="create" />
    </MaintenanceGuard>
  );
}
