"use client";

import { Menu } from "lucide-react";

import { LogoutButton } from "@/components/auth/logout-button";
import { useSession } from "@/hooks/use-session";
import { canSeeAdminNavigation, isMantenimiento, isOperador } from "@/lib/permissions";

export function AppTopbar({ onOpenAdminMenu }: { onOpenAdminMenu?: () => void }) {
  const { user } = useSession();
  const operador = isOperador(user);
  const mantenimiento = isMantenimiento(user);
  const admin = canSeeAdminNavigation(user);

  return (
    <header
      className={`sticky top-0 z-20 flex items-center justify-between px-4 py-4 backdrop-blur md:px-6 lg:px-8 ${
          operador || mantenimiento
            ? "border-b border-white/10 bg-slate-950/90 text-white lg:bg-white lg:text-slate-950 lg:border-slate-200"
            : "border-b border-slate-200 bg-white/90"
      }`}
    >
      <div className="flex items-center gap-3">
        {admin ? (
          <button
            aria-label="Abrir menú administrativo"
            className="inline-flex rounded-2xl border border-slate-200 bg-white p-2 text-slate-700 shadow-sm transition hover:bg-slate-50 lg:hidden"
            onClick={onOpenAdminMenu}
            type="button"
          >
            <Menu className="h-5 w-5" />
          </button>
        ) : null}
        <div>
          <p
            className={`text-xs font-semibold uppercase tracking-[0.24em] ${
              operador || mantenimiento ? "text-brand-300 lg:text-brand-700" : "text-brand-700"
            }`}
          >
            {mantenimiento ? "Mantenimiento" : "Operacion"}
          </p>
          <h1
            className={
              operador || mantenimiento
                ? "text-lg font-semibold text-white lg:text-slate-950"
                : "text-lg font-semibold text-slate-950"
            }
          >
            {operador ? "Tu jornada" : mantenimiento ? "Órdenes de taller" : "Panel de viajes"}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div
          className={`hidden rounded-2xl px-4 py-2 text-right md:block ${
            operador || mantenimiento
              ? "border border-white/10 bg-white/5 lg:border-slate-200 lg:bg-slate-50"
              : "border border-slate-200 bg-slate-50"
          }`}
        >
          <p
            className={
              operador || mantenimiento
                ? "text-sm font-semibold text-white lg:text-slate-900"
                : "text-sm font-semibold text-slate-900"
            }
          >
            {user?.nombre} {user?.apellido}
          </p>
          <p
            className={
              operador || mantenimiento
                ? "text-xs uppercase tracking-[0.2em] text-slate-300 lg:text-slate-500"
                : "text-xs uppercase tracking-[0.2em] text-slate-500"
            }
          >
            {user?.rol}
          </p>
        </div>
        <LogoutButton />
      </div>
    </header>
  );
}
