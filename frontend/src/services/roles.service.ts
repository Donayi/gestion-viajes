import { apiFetch } from "@/services/api-client";
import type { CreateRolePayload, Role, UpdateRolePayload } from "@/types/role";

export function getRolesRequest() {
  return apiFetch<Role[]>("/roles");
}

export function createRoleRequest(payload: CreateRolePayload) {
  return apiFetch<Role>("/roles", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function updateRoleRequest(roleId: number, payload: UpdateRolePayload) {
  return apiFetch<Role>(`/roles/${roleId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function deleteRoleRequest(roleId: number) {
  return apiFetch<void>(`/roles/${roleId}`, {
    method: "DELETE"
  });
}
