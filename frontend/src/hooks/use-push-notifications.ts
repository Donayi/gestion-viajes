"use client";

import { useEffect, useMemo, useState } from "react";

import { env } from "@/lib/env";
import { getPushStatusRequest, sendPushTestRequest, subscribePushRequest, unsubscribePushRequest } from "@/services/push.service";
import type { BrowserPushPermission, PushStatusResponse, PushSubscriptionPayload } from "@/types/push";

function isPushSupported() {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return Uint8Array.from(rawData, (char) => char.charCodeAt(0));
}

function arrayBufferToBase64Url(value: ArrayBuffer | null) {
  if (!value) {
    return "";
  }

  const bytes = new Uint8Array(value);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return window.btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function buildPayload(subscription: PushSubscription): PushSubscriptionPayload {
  const json = subscription.toJSON();
  return {
    endpoint: subscription.endpoint,
    keys: {
      p256dh: json.keys?.p256dh ?? arrayBufferToBase64Url(subscription.getKey("p256dh")),
      auth: json.keys?.auth ?? arrayBufferToBase64Url(subscription.getKey("auth"))
    },
    user_agent: navigator.userAgent
  };
}

export function usePushNotifications(enabled: boolean) {
  const [permission, setPermission] = useState<BrowserPushPermission>("unsupported");
  const [pushStatus, setPushStatus] = useState<PushStatusResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!isPushSupported()) {
      setPermission("unsupported");
      return;
    }

    setPermission(Notification.permission);
  }, []);

  async function refreshStatus() {
    if (!enabled || !isPushSupported()) {
      return;
    }

    try {
      setPushStatus(await getPushStatusRequest());
    } catch (currentError) {
      if (currentError instanceof Error) {
        setError(currentError.message);
      }
    }
  }

  useEffect(() => {
    void refreshStatus();
  }, [enabled]);

  const active = useMemo(() => Boolean(pushStatus?.has_active_subscriptions), [pushStatus]);

  async function subscribe() {
    if (!enabled || !isPushSupported()) {
      setError("Este navegador no soporta notificaciones web.");
      return false;
    }

    if (!env.webPushPublicKey) {
      setError("La clave pública de Web Push no está configurada.");
      return false;
    }

    setBusy(true);
    setError(null);
    setSuccessMessage(null);

    try {
      let currentPermission = Notification.permission;
      if (currentPermission !== "granted") {
        currentPermission = await Notification.requestPermission();
        setPermission(currentPermission);
      }

      if (currentPermission !== "granted") {
        setError("El permiso de notificaciones no fue concedido.");
        return false;
      }

      const registration = await navigator.serviceWorker.ready;
      const existing = await registration.pushManager.getSubscription();
      const subscription =
        existing ??
        (await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(env.webPushPublicKey)
        }));

      await subscribePushRequest(buildPayload(subscription));
      await refreshStatus();
      setSuccessMessage("Notificaciones activadas en este dispositivo.");
      return true;
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "No fue posible activar las notificaciones.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function unsubscribe() {
    if (!enabled || !isPushSupported()) {
      return false;
    }

    setBusy(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await unsubscribePushRequest(subscription.endpoint);
        await subscription.unsubscribe();
      }
      await refreshStatus();
      setSuccessMessage("Notificaciones desactivadas en este dispositivo.");
      return true;
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "No fue posible desactivar las notificaciones.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function sendTest() {
    if (!enabled) {
      return false;
    }

    setBusy(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await sendPushTestRequest();
      if (!response.enviado) {
        setError(response.mensaje);
        return false;
      }
      setSuccessMessage(response.mensaje);
      return true;
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "No fue posible enviar la prueba.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  return {
    active,
    busy,
    enabledByBackend: Boolean(pushStatus?.enabled && pushStatus?.vapid_public_key_configured),
    error,
    permission,
    pushStatus,
    refreshStatus,
    sendTest,
    subscribe,
    successMessage,
    unsubscribe
  };
}
