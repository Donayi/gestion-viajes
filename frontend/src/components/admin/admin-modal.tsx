"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function AdminModal({
  open,
  title,
  description,
  onClose,
  children
}: {
  open: boolean;
  title: string;
  description: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-slate-950/45 backdrop-blur-sm md:items-center md:justify-center">
      <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-[2rem] bg-white px-5 pb-8 pt-5 shadow-2xl md:max-w-2xl md:rounded-[2rem]">
        <div className="mx-auto h-1.5 w-14 rounded-full bg-slate-200 md:hidden" />
        <div className="mt-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
              Creación
            </p>
            <h3 className="mt-2 text-2xl font-semibold text-slate-950">{title}</h3>
            <p className="mt-2 text-sm text-slate-600">{description}</p>
          </div>
          <Button onClick={onClose} type="button" variant="ghost">
            Cerrar
          </Button>
        </div>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}
