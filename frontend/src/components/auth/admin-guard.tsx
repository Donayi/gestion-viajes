"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useSession } from "@/hooks/use-session";
import { canSeeAdminNavigation } from "@/lib/permissions";
import { LoadingState } from "@/components/ui/loading-state";

export function AdminGuard({ children }: { children: ReactNode }) {
  const { status, user } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status !== "loading" && !canSeeAdminNavigation(user)) {
      router.replace("/dashboard");
    }
  }, [router, status, user]);

  if (status === "loading") {
    return <LoadingState label="Validando acceso administrativo..." />;
  }

  if (!canSeeAdminNavigation(user)) {
    return <LoadingState label="Redirigiendo al dashboard..." />;
  }

  return <>{children}</>;
}
