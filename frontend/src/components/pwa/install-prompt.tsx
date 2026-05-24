"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import type { BeforeInstallPromptEvent } from "@/types/pwa";

const DISMISS_KEY = "dafreq_pwa_install_prompt_dismissed_at";
const DISMISS_MS = 7 * 24 * 60 * 60 * 1000;

function isStandaloneMode() {
  if (typeof window === "undefined") {
    return false;
  }

  const mediaMatch = window.matchMedia?.("(display-mode: standalone)").matches ?? false;
  const iosStandalone =
    typeof navigator !== "undefined" &&
    "standalone" in navigator &&
    Boolean((navigator as Navigator & { standalone?: boolean }).standalone);

  return mediaMatch || iosStandalone;
}

function isIosDevice(userAgent: string) {
  return /iphone|ipad|ipod/i.test(userAgent);
}

function shouldHideByDismissPreference() {
  const dismissedAt = window.localStorage.getItem(DISMISS_KEY);
  if (!dismissedAt) {
    return false;
  }

  const timestamp = Number(dismissedAt);
  if (!Number.isFinite(timestamp)) {
    return false;
  }

  return Date.now() - timestamp < DISMISS_MS;
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isStandalone, setIsStandalone] = useState(true);
  const [isIos, setIsIos] = useState(false);
  const [hiddenByPreference, setHiddenByPreference] = useState(true);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const userAgent = window.navigator.userAgent;
    setIsIos(isIosDevice(userAgent));
    setIsStandalone(isStandaloneMode());
    setHiddenByPreference(shouldHideByDismissPreference());

    function handleBeforeInstallPrompt(event: Event) {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    }

    function handleInstalled() {
      setDeferredPrompt(null);
      setIsStandalone(true);
      window.localStorage.removeItem(DISMISS_KEY);
    }

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  const canShowBanner = useMemo(() => {
    if (isStandalone || hiddenByPreference) {
      return false;
    }

    if (isIos) {
      return true;
    }

    return deferredPrompt !== null;
  }, [deferredPrompt, hiddenByPreference, isIos, isStandalone]);

  function handleLater() {
    window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setHiddenByPreference(true);
  }

  async function handleInstall() {
    if (!deferredPrompt) {
      return;
    }

    setInstalling(true);

    try {
      await deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice.outcome === "accepted") {
        setDeferredPrompt(null);
        setHiddenByPreference(true);
        window.localStorage.removeItem(DISMISS_KEY);
        return;
      }
    } finally {
      setInstalling(false);
    }

    handleLater();
  }

  if (!canShowBanner) {
    return null;
  }

  return (
    <div className="fixed inset-x-4 bottom-4 z-[70] mx-auto max-w-md rounded-3xl border border-brand-200 bg-white/96 p-4 shadow-2xl shadow-slate-950/15 backdrop-blur">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">
        Instalación rápida
      </p>
      <h2 className="mt-2 text-lg font-semibold text-slate-950">Instala DAFREQ en tu dispositivo</h2>
      <p className="mt-2 text-sm text-slate-600">
        {isIos
          ? "Para instalar en iPhone/iPad: Compartir → Agregar a pantalla de inicio."
          : "Guarda la app en tu pantalla de inicio para abrir DAFREQ como una aplicación."}
      </p>
      <div className="mt-4 flex gap-3">
        {!isIos ? (
          <Button className="flex-1" disabled={installing} onClick={() => void handleInstall()} type="button">
            {installing ? "Abriendo..." : "Instalar"}
          </Button>
        ) : null}
        <Button onClick={handleLater} type="button" variant="ghost">
          Después
        </Button>
      </div>
    </div>
  );
}
