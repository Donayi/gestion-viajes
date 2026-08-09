"use client";

import { useEffect } from "react";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
      return;
    }

    if (process.env.NODE_ENV === "development") {
      void navigator.serviceWorker
        .getRegistration("/")
        .then((registration) => registration?.unregister())
        .then(async () => {
          if (!("caches" in window)) return;
          const cacheNames = await window.caches.keys();
          await Promise.all(
            cacheNames
              .filter((cacheName) => cacheName.startsWith("DAFREQ_CACHE_"))
              .map((cacheName) => window.caches.delete(cacheName)),
          );
        })
        .catch(() => {
          // noop: limpiar cache de desarrollo nunca debe bloquear la aplicación
        });
      return;
    }

    void navigator.serviceWorker.register("/sw.js").catch(() => {
      // noop: offline support should never break the app shell
    });
  }, []);

  return null;
}
