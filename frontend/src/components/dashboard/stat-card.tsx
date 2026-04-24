import { Card } from "@/components/ui/card";

export function StatCard({
  label,
  value
}: {
  label: string;
  value: string | number;
}) {
  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-slate-950">{value}</p>
    </Card>
  );
}
