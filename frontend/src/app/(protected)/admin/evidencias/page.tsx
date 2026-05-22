"use client";

import { FileImage } from "lucide-react";

import { AdminPlaceholder } from "@/components/admin/admin-placeholder";
import { AdminPageHeader } from "@/components/admin/admin-page-header";

export default function AdminEvidenciasPage() {
  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Administración"
        title="Evidencias"
        description="Espacio reservado para concentrar evidencias operativas y consultas administrativas."
      />
      <AdminPlaceholder
        icon={FileImage}
        title="Módulo de evidencias"
        description="Aquí vivirá la administración central de evidencias para revisión, filtros y trazabilidad documental."
      />
    </div>
  );
}
