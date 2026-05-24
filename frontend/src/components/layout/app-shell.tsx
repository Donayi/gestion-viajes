"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useSession } from "@/hooks/use-session";
import { LocationStatusChip } from "@/components/location/location-status-chip";
import { canSeeAdminNavigation, isMantenimiento, isOperador } from "@/lib/permissions";
import { AdminMobileDrawer, AppSidebar } from "@/components/layout/app-sidebar";
import { AppTopbar } from "@/components/layout/app-topbar";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const operador = isOperador(user);
  const mantenimiento = isMantenimiento(user);
  const admin = canSeeAdminNavigation(user);
  const [adminMenuOpen, setAdminMenuOpen] = useState(false);

  useEffect(() => {
    if (mantenimiento && !pathname.startsWith("/mantenimiento")) {
      router.replace("/mantenimiento");
    }
  }, [mantenimiento, pathname, router]);

  useEffect(() => {
    setAdminMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!adminMenuOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setAdminMenuOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [adminMenuOpen]);

  return (
    <div
      className={`min-h-screen text-slate-950 ${
        operador || mantenimiento
          ? "bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.22),_transparent_25%),linear-gradient(180deg,#020617_0%,#0f172a_35%,#111827_100%)]"
          : "bg-slate-100"
      }`}
    >
      <div className="flex min-h-screen">
        <AppSidebar />
        {admin ? <AdminMobileDrawer onClose={() => setAdminMenuOpen(false)} open={adminMenuOpen} /> : null}
        <div className="flex min-h-screen flex-1 flex-col">
          <AppTopbar onOpenAdminMenu={admin ? () => setAdminMenuOpen(true) : undefined} />
          <main
            className={`flex-1 px-4 py-6 pb-28 md:px-6 lg:px-8 lg:pb-8 ${
              operador || mantenimiento ? "mx-auto w-full max-w-3xl" : ""
            }`}
          >
            {operador || mantenimiento ? (
              <div className="mb-4 lg:hidden">
                <LocationStatusChip />
              </div>
            ) : null}
            {children}
          </main>
        </div>
      </div>
      <MobileBottomNav />
    </div>
  );
}
