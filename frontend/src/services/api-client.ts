import { clearStoredToken, getStoredToken } from "@/lib/auth-storage";
import { env } from "@/lib/env";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | null;
  auth?: boolean;
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = options.auth === false ? null : getStoredToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${env.apiUrl}${path}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    clearStoredToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError("Sesion expirada", 401);
  }

  if (!response.ok) {
    let message = "Ocurrio un error inesperado";

    try {
      const payload = (await response.json()) as { detail?: string; message?: string };
      if (payload?.detail) {
        message = payload.detail;
      } else if (payload?.message) {
        message = payload.message;
      }
    } catch {
      try {
        const text = await response.text();
        if (text.trim()) {
          message = text.trim();
        }
      } catch {
        // ignore parse failure
      }
    }

    if (response.status === 403 && message === "Ocurrio un error inesperado") {
      message = "No tienes permisos para esta accion";
    }

    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
