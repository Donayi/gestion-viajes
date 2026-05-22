"use client";

import { UserCog } from "lucide-react";

import { AdminPlaceholder } from "@/components/admin/admin-placeholder";
import { AdminPageHeader } from "@/components/admin/admin-page-header";

export default function AdminPerfilPage() {
  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Sistema"
        title="Perfil administrativo"
        description="Espacio reservado para la configuración del perfil del administrador y preferencias de sesión."
      />
      <AdminPlaceholder
        icon={UserCog}
        title="Perfil de administrador"
        description="Aquí se concentrarán los datos de perfil, ajustes personales y preferencias de operación del usuario administrador."
      />
    </div>
  );
}
