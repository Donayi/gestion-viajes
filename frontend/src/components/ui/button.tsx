"use client";

import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "warning" | "success" | "ghost" | "outline";
  size?: "sm" | "md" | "lg" | "icon";
  loading?: boolean;
};

export function Button({
  children,
  className,
  disabled,
  loading = false,
  size = "md",
  type = "button",
  variant = "primary",
  ...props
}: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        size === "sm" && "min-h-9 px-3 py-2 text-sm",
        size === "md" && "min-h-10 px-4 py-2.5 text-sm",
        size === "lg" && "min-h-12 px-5 py-3 text-base",
        size === "icon" && "h-10 w-10 p-0",
        variant === "primary" && "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-400",
        variant === "secondary" && "bg-slate-100 text-slate-900 hover:bg-slate-200",
        variant === "danger" && "bg-red-600 text-white hover:bg-red-700 focus:ring-red-400",
        variant === "warning" && "bg-amber-500 text-white hover:bg-amber-600 focus:ring-amber-300",
        variant === "success" && "bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-400",
        variant === "ghost" && "bg-transparent text-slate-700 hover:bg-slate-100 focus:ring-slate-300",
        variant === "outline" && "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus:ring-slate-300",
        className
      )}
      disabled={disabled || loading}
      type={type}
      {...props}
    >
      {loading ? "Procesando..." : children}
    </button>
  );
}
