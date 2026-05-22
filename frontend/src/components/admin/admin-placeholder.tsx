"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export function AdminPlaceholder({
  icon: Icon,
  title,
  description,
  href = "/dashboard",
  cta = "Volver al dashboard"
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  href?: string;
  cta?: string;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-[2rem] border border-brand-100 bg-gradient-to-br from-slate-950 via-brand-950 to-brand-800 p-8 text-white shadow-soft">
        <div className="flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-white/10">
          <Icon className="h-8 w-8 text-brand-100" />
        </div>
        <p className="mt-6 text-xs font-semibold uppercase tracking-[0.24em] text-brand-200">
          Próximamente
        </p>
        <h1 className="mt-3 text-3xl font-semibold">{title}</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-200">{description}</p>
      </div>

      <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
        <p className="text-sm text-slate-600">
          Este módulo ya tiene espacio reservado dentro del menú administrativo para mantener la
          navegación consistente mientras se completa la siguiente fase de operación.
        </p>

        <div className="mt-5 flex flex-wrap gap-3">
          <Link href={href}>
            <Button type="button">{cta}</Button>
          </Link>
          <Link href="/viajes">
            <Button type="button" variant="secondary">
              Ir a viajes
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
