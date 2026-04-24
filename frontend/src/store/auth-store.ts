import type { CurrentUser } from "@/types/auth";

export type AuthState = {
  user: CurrentUser | null;
  token: string | null;
  status: "loading" | "authenticated" | "anonymous";
};
