"use client";

import { BellRing, BellOff, Send, Smartphone } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { usePushNotifications } from "@/hooks/use-push-notifications";
import { useSession } from "@/hooks/use-session";

type Props = {
  compact?: boolean;
};

function resolveStatusLabel(permission: ReturnType<typeof usePushNotifications>["permission"], active: boolean) {
  if (permission === "unsupported") {
    return "No soportado";
  }
  if (permission === "denied") {
    return "Denegado";
  }
  if (active) {
    return "Activo";
  }
  if (permission === "granted") {
    return "Permitido";
  }
  return "Pendiente";
}

export function PushNotificationSettings({ compact = false }: Props) {
  const { status } = useSession();
  const {
    active,
    busy,
    enabledByBackend,
    error,
    permission,
    pushStatus,
    sendTest,
    subscribe,
    successMessage,
    unsubscribe
  } = usePushNotifications(status === "authenticated");

  return (
    <Card className={compact ? "rounded-[1.5rem] border-slate-200 p-4 shadow-none" : "p-6"}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-1 rounded-2xl bg-brand-50 p-2 text-brand-700">
            <Smartphone className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
              Notificaciones del dispositivo
            </p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Push web en esta PWA</h3>
            <p className="mt-2 text-sm text-slate-600">
              Recibe avisos de viajes, standby, mantenimiento y alertas relevantes directamente en el dispositivo.
            </p>
          </div>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
          {resolveStatusLabel(permission, active)}
        </span>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
        DAFREQ solo envía el título, un mensaje breve y el enlace de regreso a la app. No se guardan datos sensibles
        en el service worker.
      </div>

      {!enabledByBackend ? (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Web Push todavía no está configurado completamente en el entorno actual.
        </div>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {successMessage ? (
        <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {successMessage}
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Permiso</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{permission}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Suscripciones activas</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{pushStatus?.active_subscriptions_count ?? 0}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Estado backend</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{enabledByBackend ? "Listo" : "Pendiente"}</p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        {active ? (
          <Button disabled={busy} onClick={() => void unsubscribe()} type="button" variant="warning">
            <BellOff className="h-4 w-4" />
            Desactivar notificaciones
          </Button>
        ) : (
          <Button disabled={busy || !enabledByBackend} onClick={() => void subscribe()} type="button">
            <BellRing className="h-4 w-4" />
            Activar notificaciones
          </Button>
        )}
        <Button disabled={busy || !active} onClick={() => void sendTest()} type="button" variant="secondary">
          <Send className="h-4 w-4" />
          Enviar prueba
        </Button>
      </div>
    </Card>
  );
}
