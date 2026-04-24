"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const items = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/viajes", label: "Viajes" }
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white xl:flex xl:flex-col">
      <div className="border-b border-slate-200 px-8 py-8">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand-700">
          Plataforma
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-slate-950">Gestion de Viajes</h2>
      </div>

      <nav className="flex flex-1 flex-col gap-2 px-5 py-6">
        {items.map((item) => (
          <Link
            key={item.href}
            className={cn(
              "rounded-2xl px-4 py-3 text-sm font-medium transition",
              pathname === item.href
                ? "bg-brand-700 text-white"
                : "text-slate-700 hover:bg-slate-100"
            )}
            href={item.href}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
