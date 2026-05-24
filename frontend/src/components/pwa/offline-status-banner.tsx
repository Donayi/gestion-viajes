"use client";

import { useEffect, useRef, useState } from "react";

export function OfflineStatusBanner() {
  const [offline, setOffline] = useState(false);
  const [restored, setRestored] = useState(false);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    setOffline(!window.navigator.onLine);

    function handleOffline() {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      setRestored(false);
      setOffline(true);
    }

    function handleOnline() {
      setOffline(false);
      setRestored(true);
      timeoutRef.current = window.setTimeout(() => {
        setRestored(false);
      }, 3500);
    }

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);

    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  if (!offline && !restored) {
    return null;
  }

  return (
    <div className="fixed inset-x-4 bottom-24 z-[75] mx-auto max-w-2xl rounded-2xl border px-4 py-3 text-sm shadow-xl backdrop-blur md:bottom-6">
      <div
        className={
          offline
            ? "rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900"
            : "rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-800"
        }
      >
        {offline
          ? "Sin conexión. Puedes consultar contenido previamente cargado, pero las operaciones requieren internet."
          : "Conexión restaurada."}
      </div>
    </div>
  );
}
