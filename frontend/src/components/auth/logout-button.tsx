"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useSession } from "@/hooks/use-session";

export function LogoutButton() {
  const router = useRouter();
  const { logout } = useSession();

  return (
    <Button
      className="bg-slate-900 hover:bg-slate-800"
      onClick={() => {
        logout();
        router.replace("/login");
      }}
      type="button"
      variant="secondary"
    >
      Salir
    </Button>
  );
}
