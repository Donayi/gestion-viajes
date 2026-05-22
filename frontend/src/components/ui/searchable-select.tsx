"use client";

import { useId } from "react";

import { cn } from "@/lib/cn";

type SearchableSelectOption = {
  value: string;
  label: string;
  description?: string | null;
};

type Props = {
  label: string;
  placeholder?: string;
  value: string;
  options: SearchableSelectOption[];
  className?: string;
  emptyLabel?: string;
  onChange: (value: string) => void;
};

export function SearchableSelect({
  label,
  placeholder,
  value,
  options,
  className,
  emptyLabel = "Todos",
  onChange,
}: Props) {
  const datalistId = useId();

  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        className={cn(
          "w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-200",
          className
        )}
        list={datalistId}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder ?? emptyLabel}
        value={value}
      />
      <datalist id={datalistId}>
        <option value="">{emptyLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.label}>
            {option.description ? `${option.label} - ${option.description}` : option.label}
          </option>
        ))}
      </datalist>
    </label>
  );
}
