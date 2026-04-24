"use client";

import { LogoutButton } from "@/components/auth/logout-button";
import { useSession } from "@/hooks/use-session";
import { isOperador } from "@/lib/permissions";

export function AppTopbar() {
  const { user } = useSession();
  const operador = isOperador(user);

  return (
    <header
      className={`sticky top-0 z-20 flex items-center justify-between px-4 py-4 backdrop-blur md:px-6 xl:px-8 ${
        operador
          ? "border-b border-white/10 bg-slate-950/90 text-white xl:bg-white xl:text-slate-950 xl:border-slate-200"
          : "border-b border-slate-200 bg-white/90"
      }`}
    >
      <div>
        <p
          className={`text-xs font-semibold uppercase tracking-[0.24em] ${
            operador ? "text-brand-300 xl:text-brand-700" : "text-brand-700"
          }`}
        >
          Operacion
        </p>
        <h1 className={operador ? "text-lg font-semibold text-white xl:text-slate-950" : "text-lg font-semibold text-slate-950"}>
          {operador ? "Tu jornada" : "Panel de viajes"}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <div
          className={`hidden rounded-2xl px-4 py-2 text-right md:block ${
            operador
              ? "border border-white/10 bg-white/5 xl:border-slate-200 xl:bg-slate-50"
              : "border border-slate-200 bg-slate-50"
          }`}
        >
          <p className={operador ? "text-sm font-semibold text-white xl:text-slate-900" : "text-sm font-semibold text-slate-900"}>
            {user?.nombre} {user?.apellido}
          </p>
          <p className={operador ? "text-xs uppercase tracking-[0.2em] text-slate-300 xl:text-slate-500" : "text-xs uppercase tracking-[0.2em] text-slate-500"}>
            {user?.rol}
          </p>
        </div>
        <LogoutButton />
      </div>
    </header>
  );
}
