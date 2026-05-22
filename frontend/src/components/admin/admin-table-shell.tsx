import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";

export function AdminTableShell({
  title,
  action,
  children
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card className="overflow-hidden border-brand-100">
      <div className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
        <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
        {action}
      </div>
      <div className="overflow-x-auto">{children}</div>
    </Card>
  );
}
