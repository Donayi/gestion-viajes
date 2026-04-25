import type { CurrentUser } from "@/types/auth";

export function isAdmin(user: CurrentUser | null) {
  return user?.rol?.startsWith("ADMIN") ?? false;
}

export function isOperador(user: CurrentUser | null) {
  return user?.rol === "OPERADOR";
}
