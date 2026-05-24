"use client";

import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";

import { cn } from "@/lib/cn";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  allowPasswordToggle?: boolean;
};

export function Input({ allowPasswordToggle = false, className, label, type, ...props }: Props) {
  const [showPassword, setShowPassword] = useState(false);
  const isPasswordField = type === "password";
  const canTogglePassword = allowPasswordToggle && isPasswordField;
  const resolvedType = canTogglePassword ? (showPassword ? "text" : "password") : type;

  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <div className="relative">
        <input
          className={cn(
            "w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-200",
            canTogglePassword ? "pr-12" : "",
            className
          )}
          type={resolvedType}
          {...props}
        />
        {canTogglePassword ? (
          <button
            aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            className="absolute inset-y-0 right-3 flex items-center text-slate-500 transition-colors hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
            onClick={(event) => {
              event.preventDefault();
              setShowPassword((current) => !current);
            }}
            type="button"
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        ) : null}
      </div>
    </label>
  );
}
