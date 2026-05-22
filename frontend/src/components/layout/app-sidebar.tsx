"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, X } from "lucide-react";

import { cn } from "@/lib/cn";
import { useSession } from "@/hooks/use-session";
import { canSeeAdminNavigation } from "@/lib/permissions";
import { adminNavigationSections } from "@/lib/navigation";

function AdminNavigationContent({
  pathname,
  onNavigate
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex flex-1 flex-col gap-6 overflow-y-auto px-5 py-6">
      {adminNavigationSections.map((section) => (
        <div key={section.title} className="space-y-2">
          <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            {section.title}
          </p>
          <div className="space-y-1.5">
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

              return (
                <Link
                  key={item.href}
                  className={cn(
                    "group flex items-center gap-3 rounded-[1.35rem] px-4 py-3 text-sm font-medium transition-all",
                    isActive
                      ? "bg-white text-slate-950 shadow-soft"
                      : "text-slate-200 hover:bg-white/10 hover:text-white"
                  )}
                  href={item.href}
                  onClick={onNavigate}
                >
                  <span
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-2xl transition",
                      isActive
                        ? "bg-brand-100 text-brand-700"
                        : "bg-white/5 text-brand-200 group-hover:bg-white/10"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="flex-1">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

function SidebarFooter({
  userName,
  role,
  onLogout
}: {
  userName: string;
  role?: string | null;
  onLogout: () => void;
}) {
  return (
    <div className="border-t border-white/10 px-5 py-5">
      <div className="rounded-[1.5rem] border border-white/10 bg-white/5 px-4 py-4">
        <p className="text-sm font-semibold text-white">{userName}</p>
        <p className="mt-1 text-xs uppercase tracking-[0.22em] text-slate-400">{role}</p>

        <button
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/15"
          onClick={onLogout}
          type="button"
        >
          <LogOut className="h-4 w-4" />
          Salir
        </button>
      </div>
    </div>
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useSession();
  const admin = canSeeAdminNavigation(user);

  if (!admin) {
    return null;
  }

  return (
    <aside className="hidden w-80 shrink-0 border-r border-white/10 bg-[linear-gradient(180deg,#020617_0%,#0f172a_30%,#0b1f4d_100%)] text-white shadow-2xl lg:flex lg:flex-col">
      <div className="border-b border-white/10 px-7 py-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand-200">
          Plataforma
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-white">Gestión de Viajes</h2>
        <p className="mt-2 text-sm text-slate-300">
          Centro administrativo para operación, catálogos y seguimiento ejecutivo.
        </p>
      </div>

      <AdminNavigationContent pathname={pathname} />
      <SidebarFooter
        onLogout={() => {
          logout();
          router.replace("/login");
        }}
        role={user?.rol}
        userName={`${user?.nombre ?? ""} ${user?.apellido ?? ""}`.trim()}
      />
    </aside>
  );
}

export function AdminMobileDrawer({
  open,
  onClose
}: {
  open: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useSession();
  const admin = canSeeAdminNavigation(user);

  if (!admin) {
    return null;
  }

  return (
    <div
      aria-hidden={!open}
      className={cn(
        "fixed inset-0 z-40 lg:hidden",
        open ? "pointer-events-auto" : "pointer-events-none"
      )}
    >
      <button
        aria-label="Cerrar menú"
        className={cn(
          "absolute inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity",
          open ? "opacity-100" : "opacity-0"
        )}
        onClick={onClose}
        type="button"
      />
      <aside
        className={cn(
          "absolute left-0 top-0 flex h-full w-[88vw] max-w-sm flex-col border-r border-white/10 bg-[linear-gradient(180deg,#020617_0%,#0f172a_30%,#0b1f4d_100%)] text-white shadow-2xl transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-start justify-between border-b border-white/10 px-6 py-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand-200">
              Plataforma
            </p>
            <h2 className="mt-3 text-xl font-semibold text-white">Menú administrativo</h2>
            <p className="mt-2 text-sm text-slate-300">Navega módulos y catálogos desde móvil.</p>
          </div>
          <button
            aria-label="Cerrar menú"
            className="rounded-2xl border border-white/10 bg-white/10 p-2 text-white transition hover:bg-white/15"
            onClick={onClose}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <AdminNavigationContent onNavigate={onClose} pathname={pathname} />
        <SidebarFooter
          onLogout={() => {
            onClose();
            logout();
            router.replace("/login");
          }}
          role={user?.rol}
          userName={`${user?.nombre ?? ""} ${user?.apellido ?? ""}`.trim()}
        />
      </aside>
    </div>
  );
}
