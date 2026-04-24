import { apiFetch } from "@/services/api-client";
import type { CurrentUser, TokenResponse } from "@/types/auth";

export async function loginRequest(username: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body,
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    auth: false
  });
}

export function getMeRequest() {
  return apiFetch<CurrentUser>("/auth/me");
}
