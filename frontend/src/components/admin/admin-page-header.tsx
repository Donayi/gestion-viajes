export function AdminPageHeader({
  eyebrow,
  title,
  description
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <section className="rounded-[2rem] bg-gradient-to-r from-brand-800 via-brand-700 to-slate-900 px-6 py-7 text-white shadow-soft">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/70">{eyebrow}</p>
      <h1 className="mt-3 text-3xl font-semibold">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm text-white/80">{description}</p>
    </section>
  );
}
