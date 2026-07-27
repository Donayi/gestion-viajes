import { apiFetch } from "@/services/api-client";
import type { AdminDashboardResponse } from "@/types/dashboard";


export function getAdminDashboardRequest(signal?: AbortSignal) {
  return apiFetch<AdminDashboardResponse>("/dashboard/admin", { signal });
}
