import type { ReactNode } from "react";

import { SessionGuard } from "@/components/auth/session-guard";
import { AppShell } from "@/components/layout/app-shell";
import { LocationProvider } from "@/context/location-context";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <SessionGuard>
      <LocationProvider>
        <AppShell>{children}</AppShell>
      </LocationProvider>
    </SessionGuard>
  );
}
