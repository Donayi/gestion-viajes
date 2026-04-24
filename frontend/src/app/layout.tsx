import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/components/auth/auth-provider";

import "@/app/globals.css";

export const metadata: Metadata = {
  title: "Gestion de Viajes",
  description: "Frontend operativo para la plataforma logistica"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
