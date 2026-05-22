import type { CurrentUser } from "@/types/auth";

export function isAdmin(user: CurrentUser | null) {
  return user?.rol?.startsWith("ADMIN") ?? false;
}

export function isOperador(user: CurrentUser | null) {
  return user?.rol === "OPERADOR";
}

export function isMantenimiento(user: CurrentUser | null) {
  return user?.rol === "MANTENIMIENTO";
}

export function canSeeAdminNavigation(user: CurrentUser | null) {
  return isAdmin(user);
}

export function canSeeOperatorNavigation(user: CurrentUser | null) {
  return isOperador(user);
}

export function canSeeMaintenanceNavigation(user: CurrentUser | null) {
  return isMantenimiento(user);
}

export function getDefaultRouteForUser(user: CurrentUser | null) {
  if (isAdmin(user)) {
    return "/dashboard";
  }
  if (isOperador(user)) {
    return "/dashboard";
  }
  if (isMantenimiento(user)) {
    return "/mantenimiento";
  }
  return "/login";
}
