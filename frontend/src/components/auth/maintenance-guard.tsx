"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useSession } from "@/hooks/use-session";
import { isMantenimiento } from "@/lib/permissions";
import { LoadingState } from "@/components/ui/loading-state";

export function MaintenanceGuard({ children }: { children: ReactNode }) {
  const { status, user } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status !== "loading" && !isMantenimiento(user)) {
      router.replace("/dashboard");
    }
  }, [router, status, user]);

  if (status === "loading") {
    return <LoadingState label="Validando acceso de mantenimiento..." />;
  }

  if (!isMantenimiento(user)) {
    return <LoadingState label="Redirigiendo..." />;
  }

  return <>{children}</>;
}
