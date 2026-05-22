"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type StatusBadgeVariant =
  | "primary"
  | "active"
  | "inactive"
  | "warning"
  | "danger"
  | "success"
  | "info"
  | "neutral";

export function StatusBadge({
  children,
  className,
  variant = "neutral",
}: {
  children: ReactNode;
  className?: string;
  variant?: StatusBadgeVariant;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]",
        variant === "primary" && "border-blue-200 bg-blue-600 text-white",
        variant === "active" && "border-blue-200 bg-blue-50 text-blue-700",
        variant === "inactive" && "border-slate-200 bg-slate-100 text-slate-600",
        variant === "warning" && "border-amber-200 bg-amber-50 text-amber-700",
        variant === "danger" && "border-red-200 bg-red-50 text-red-700",
        variant === "success" && "border-emerald-200 bg-emerald-50 text-emerald-700",
        variant === "info" && "border-sky-200 bg-sky-50 text-sky-700",
        variant === "neutral" && "border-slate-200 bg-white text-slate-700",
        className
      )}
    >
      {children}
    </span>
  );
}
