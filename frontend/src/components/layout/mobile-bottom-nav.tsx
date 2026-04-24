"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useSession } from "@/hooks/use-session";
import { isOperador } from "@/lib/permissions";
import { cn } from "@/lib/cn";

const items = [
  { href: "/dashboard", label: "Inicio" },
  { href: "/viajes", label: "Viajes" }
];

export function MobileBottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useSession();

  if (!isOperador(user)) {
    return null;
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-30 border-t border-white/10 bg-slate-950/95 px-4 py-3 backdrop-blur xl:hidden">
      <div className="grid grid-cols-3 gap-3">
        {items.map((item) => (
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
            {item.label}
          </Link>
        ))}
        <button
          className="rounded-2xl bg-white/5 px-4 py-3 text-center text-sm font-medium text-slate-200"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
          type="button"
        >
          Perfil / Salir
        </button>
      </div>
    </nav>
  );
}
