import type { CurrentUser } from "@/types/auth";

export function isAdmin(user: CurrentUser | null) {
  return user?.rol === "ADMIN";
}

export function isOperador(user: CurrentUser | null) {
  return user?.rol === "OPERADOR";
}
