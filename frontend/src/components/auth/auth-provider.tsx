"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/auth-storage";
import { getMeRequest, loginRequest } from "@/services/auth.service";
import type { CurrentUser } from "@/types/auth";

type AuthContextValue = {
  user: CurrentUser | null;
  status: "loading" | "authenticated" | "anonymous";
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "authenticated" | "anonymous">("loading");

  const logout = useCallback(() => {
    clearStoredToken();
    setToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const refreshSession = useCallback(async () => {
    const storedToken = getStoredToken();

    if (!storedToken) {
      setStatus("anonymous");
      setToken(null);
      setUser(null);
      return;
    }

    try {
      setStatus("loading");
      setToken(storedToken);
      const currentUser = await getMeRequest();
      setUser(currentUser);
      setStatus("authenticated");
    } catch {
      logout();
    }
  }, [logout]);

  const login = useCallback(
    async (username: string, password: string) => {
      const response = await loginRequest(username, password);
      setStoredToken(response.access_token);
      setToken(response.access_token);
      const currentUser = await getMeRequest();
      setUser(currentUser);
      setStatus("authenticated");
    },
    []
  );

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const value = useMemo(
    () => ({
      user,
      status,
      token,
      login,
      logout,
      refreshSession
    }),
    [login, logout, refreshSession, status, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
