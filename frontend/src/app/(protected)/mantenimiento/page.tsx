import { MaintenanceGuard } from "@/components/auth/maintenance-guard";
import { MantenimientosWorkbench } from "@/app/(protected)/admin/mantenimientos/page";

export default function MantenimientoHomePage() {
  return (
    <MaintenanceGuard>
      <MantenimientosWorkbench variant="maintenance" maintenanceView="list" />
    </MaintenanceGuard>
  );
}
