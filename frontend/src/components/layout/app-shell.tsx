"use client";

import type { ReactNode } from "react";

import { useSession } from "@/hooks/use-session";
import { isOperador } from "@/lib/permissions";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppTopbar } from "@/components/layout/app-topbar";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useSession();
  const operador = isOperador(user);

  return (
    <div
      className={`min-h-screen text-slate-950 ${
        operador
          ? "bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.22),_transparent_25%),linear-gradient(180deg,#020617_0%,#0f172a_35%,#111827_100%)]"
          : "bg-slate-100"
      }`}
    >
      <div className="flex min-h-screen">
        <AppSidebar />
        <div className="flex min-h-screen flex-1 flex-col">
          <AppTopbar />
          <main
            className={`flex-1 px-4 py-6 pb-28 md:px-6 xl:px-8 xl:pb-8 ${
              operador ? "mx-auto w-full max-w-3xl" : ""
            }`}
          >
            {children}
          </main>
        </div>
      </div>
      <MobileBottomNav />
    </div>
  );
}
