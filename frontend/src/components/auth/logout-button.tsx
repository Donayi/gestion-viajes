"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useSession } from "@/hooks/use-session";

export function LogoutButton() {
  const router = useRouter();
  const { logout } = useSession();

  return (
    <Button
      onClick={() => {
        logout();
        router.replace("/login");
      }}
      size="md"
      type="button"
      variant="primary"
    >
      <LogOut className="h-4 w-4" />
      Salir
    </Button>
  );
}
