"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoadingState } from "@/components/ui/loading-state";
import { useSession } from "@/hooks/use-session";

export default function RootPage() {
  const router = useRouter();
  const { status } = useSession();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }

    if (status === "anonymous") {
      router.replace("/login");
    }
  }, [router, status]);

  return <LoadingState label="Preparando aplicacion..." />;
}
