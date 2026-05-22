"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useSession } from "@/hooks/use-session";
import { getDefaultRouteForUser } from "@/lib/permissions";

export default function RootPage() {
  const router = useRouter();
  const { status, user } = useSession();
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);

    if (status === "authenticated") {
      router.replace(getDefaultRouteForUser(user));
    }
  }, [router, status, user]);

  if (status === "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4 text-center text-white">
          <div className="h-10 w-10 animate-pulse rounded-full border-2 border-white/20 border-t-brand-400" />
          <p className="text-sm uppercase tracking-[0.24em] text-slate-300">Preparando acceso</p>
        </div>
      </div>
    );
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-6 py-12 text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.16),_transparent_38%),radial-gradient(circle_at_bottom,_rgba(14,165,233,0.14),_transparent_30%)]" />
      <div
        className={`relative w-full max-w-3xl rounded-[2rem] border border-white/10 bg-white/5 px-8 py-12 shadow-2xl backdrop-blur transition-all duration-700 md:px-12 md:py-16 ${
          isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
        }`}
      >
        <div className="flex flex-col items-center text-center">
          <Image
            src="/logo-dafreq.png"
            alt="DAFREQ Transport"
            width={164}
            height={164}
            className="h-28 w-28 object-contain drop-shadow-[0_12px_32px_rgba(15,23,42,0.45)] md:h-36 md:w-36"
            priority
          />
          <p className="mt-8 text-sm font-semibold uppercase tracking-[0.4em] text-brand-200">DAFREQ</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Logística Inteligente
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-7 text-slate-300 md:text-base">
            Plataforma operativa para viajes, disponibilidad, mantenimiento y control documental.
          </p>
          <Link
            href="/login"
            className="mt-10 inline-flex h-12 min-w-40 items-center justify-center rounded-xl bg-brand-700 px-8 text-base font-medium text-white shadow-lg shadow-brand-500/20 transition hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-300"
          >
            Ingresar
          </Link>
        </div>
      </div>
    </main>
  );
}
