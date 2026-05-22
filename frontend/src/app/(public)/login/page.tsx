"use client";

import Image from "next/image";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoginForm } from "@/components/auth/login-form";
import { useSession } from "@/hooks/use-session";
import { getDefaultRouteForUser } from "@/lib/permissions";

export default function LoginPage() {
  const router = useRouter();
  const { status, user } = useSession();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(getDefaultRouteForUser(user));
    }
  }, [router, status, user]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-white">
        <div className="flex flex-col items-center gap-4 text-center">
          <Image
            src="/logo-dafreq.png"
            alt="DAFREQ Transport"
            width={96}
            height={96}
            className="h-20 w-20 object-contain"
            priority
          />
          <p className="text-sm uppercase tracking-[0.28em] text-slate-300">Validando sesión</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-4 py-10">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_34%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.12),_transparent_32%)]" />
      <div className="grid w-full max-w-6xl gap-8 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="relative hidden rounded-[2rem] border border-white/10 bg-white/6 p-10 text-white shadow-soft backdrop-blur xl:block">
          <Image
            src="/logo-dafreq.png"
            alt="DAFREQ Transport"
            width={104}
            height={104}
            className="h-24 w-24 object-contain"
            priority
          />
          <p className="mt-8 text-sm font-semibold uppercase tracking-[0.35em] text-brand-200">DAFREQ</p>
          <h1 className="mt-5 text-5xl font-semibold leading-tight">Logística Inteligente</h1>
          <p className="mt-5 max-w-xl text-base text-slate-200">
            Accede al centro operativo para administrar viajes, mantenimiento, disponibilidad y trazabilidad logística.
          </p>
        </section>
        <section className="relative flex items-center justify-center">
          <div className="w-full max-w-md">
            <div className="mb-6 flex flex-col items-center text-center xl:hidden">
              <Image
                src="/logo-dafreq.png"
                alt="DAFREQ Transport"
                width={88}
                height={88}
                className="h-20 w-20 object-contain"
                priority
              />
              <p className="mt-5 text-sm font-semibold uppercase tracking-[0.34em] text-brand-200">DAFREQ</p>
              <h1 className="mt-3 text-3xl font-semibold text-white">Logística Inteligente</h1>
            </div>
            <LoginForm />
          </div>
        </section>
      </div>
    </div>
  );
}
