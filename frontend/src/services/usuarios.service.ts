import { apiFetch } from "@/services/api-client";
import type {
  AdminUser,
  ChangeUserPasswordPayload,
  CreateAdminUserPayload,
  UpdateAdminUserPayload
} from "@/types/user-admin";

export function getUsuariosRequest() {
  return apiFetch<AdminUser[]>("/usuarios");
}

export function createUsuarioRequest(payload: CreateAdminUserPayload) {
  return apiFetch<AdminUser>("/usuarios", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function updateUsuarioRequest(userId: number, payload: UpdateAdminUserPayload) {
  return apiFetch<AdminUser>(`/usuarios/${userId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export function deleteUsuarioRequest(userId: number) {
  return apiFetch<void>(`/usuarios/${userId}`, {
    method: "DELETE"
  });
}

export function changeUsuarioPasswordRequest(userId: number, payload: ChangeUserPasswordPayload) {
  return apiFetch<{ message: string }>(`/usuarios/${userId}/password`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}
