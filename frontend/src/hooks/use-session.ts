"use client";

import { useContext } from "react";

import { AuthContext } from "@/components/auth/auth-provider";

export function useSession() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useSession debe usarse dentro de AuthProvider");
  }

  return context;
}
