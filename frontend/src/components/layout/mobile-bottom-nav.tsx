"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { useSession } from "@/hooks/use-session";
import { canSeeMaintenanceNavigation, canSeeOperatorNavigation } from "@/lib/permissions";
import { cn } from "@/lib/cn";
import { maintenanceNavigationItems, operatorNavigationItems } from "@/lib/navigation";

export function MobileBottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useSession();

  const isOperatorNav = canSeeOperatorNavigation(user);
  const isMaintenanceNav = canSeeMaintenanceNavigation(user);

  if (!isOperatorNav && !isMaintenanceNav) {
    return null;
  }

  const items = isMaintenanceNav ? maintenanceNavigationItems : operatorNavigationItems;
  const gridClassName = isMaintenanceNav ? "grid-cols-3" : "grid-cols-4";

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-30 border-t border-white/10 bg-slate-950/95 px-4 py-3 backdrop-blur xl:hidden">
      <div className={cn("grid gap-3", gridClassName)}>
        {items.map((item) => {
          const Icon = item.icon;
          return (
          <Link
            key={item.href}
            className={cn(
              "rounded-2xl px-4 py-3 text-center text-sm font-medium transition",
              pathname === item.href
                ? "bg-brand-500 text-white shadow-soft"
                : "bg-white/5 text-slate-200"
            )}
            href={item.href}
          >
            <div className="flex flex-col items-center gap-1">
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </div>
          </Link>
          );
        })}
        <button
          className="rounded-2xl bg-white/5 px-4 py-3 text-center text-sm font-medium text-slate-200"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
          type="button"
        >
          <div className="flex flex-col items-center gap-1">
            <LogOut className="h-4 w-4" />
            <span>Salir</span>
          </div>
        </button>
      </div>
    </nav>
  );
}
