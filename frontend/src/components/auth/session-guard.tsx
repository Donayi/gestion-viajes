"use client";

import { type ReactNode, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useSession } from "@/hooks/use-session";
import { LoadingState } from "@/components/ui/loading-state";

export function SessionGuard({ children }: { children: ReactNode }) {
  const { status } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous" && pathname !== "/login") {
      router.replace("/login");
    }
  }, [pathname, router, status]);

  if (status === "loading") {
    return <LoadingState label="Validando sesion..." />;
  }

  if (status === "anonymous") {
    return null;
  }

  return <>{children}</>;
}
