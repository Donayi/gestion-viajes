export function LoadingState({ label = "Cargando..." }: { label?: string }) {
  return (
    <div className="flex min-h-[220px] items-center justify-center">
      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600 shadow-soft">
        {label}
      </div>
    </div>
  );
}
