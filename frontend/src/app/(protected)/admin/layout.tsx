import type { ReactNode } from "react";

import { AdminGuard } from "@/components/auth/admin-guard";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AdminGuard>{children}</AdminGuard>;
}
