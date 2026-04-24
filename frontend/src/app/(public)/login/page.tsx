"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoginForm } from "@/components/auth/login-form";
import { useSession } from "@/hooks/use-session";

export default function LoginPage() {
  const router = useRouter();
  const { status } = useSession();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [router, status]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="grid w-full max-w-6xl gap-8 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="hidden rounded-[2rem] bg-brand-900 p-10 text-white shadow-soft xl:block">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-brand-200">
            Plataforma logistica
          </p>
          <h1 className="mt-5 text-5xl font-semibold leading-tight">
            Opera viajes con una vista clara del workflow.
          </h1>
          <p className="mt-5 max-w-xl text-base text-brand-100">
            Consulta viajes enriquecidos, valida historial y ejecuta acciones operativas desde una misma interfaz.
          </p>
        </section>
        <section className="flex items-center justify-center">
          <LoginForm />
        </section>
      </div>
    </div>
  );
}
