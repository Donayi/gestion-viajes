"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { getPendingStandbyRequest } from "@/components/viajes/workflow-helpers";
import { useWorkflow } from "@/hooks/use-workflow";
import type { ViajeDetail, WorkflowActionPayload, WorkflowOperationalPayload } from "@/types/viaje";

type ActionOption = {
  key: "iniciar-carga" | "iniciar-viaje" | "reiniciar-viaje" | "marcar-retraso" | "finalizar";
  label: string;
  variant: "primary" | "secondary" | "warning" | "success";
  requiresKilometraje?: boolean;
  requiresDiesel?: boolean;
  requiresComment?: boolean;
};

const actions: ActionOption[] = [
  { key: "iniciar-carga", label: "Iniciar carga", variant: "secondary" },
  { key: "iniciar-viaje", label: "Iniciar viaje", variant: "primary", requiresKilometraje: true, requiresDiesel: true },
  { key: "reiniciar-viaje", label: "Reiniciar viaje", variant: "warning", requiresKilometraje: true, requiresDiesel: true },
  { key: "marcar-retraso", label: "Marcar retraso", variant: "warning", requiresComment: true },
  { key: "finalizar", label: "Finalizar", variant: "success", requiresKilometraje: true, requiresDiesel: true }
];

export function WorkflowActions({
  viaje,
  onSuccess
}: {
  viaje: ViajeDetail;
  onSuccess: () => Promise<void>;
}) {
  const isFinalizado = viaje.estatus_actual.clave === "FINALIZADO";
  const isStandby = viaje.estatus_actual.clave === "STANDBY";
  const [comentario, setComentario] = useState("");
  const [kilometraje, setKilometraje] = useState("");
  const [nivelDiesel, setNivelDiesel] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [latitud, setLatitud] = useState("");
  const [longitud, setLongitud] = useState("");
  const [showAuthorizeStandbyConfirm, setShowAuthorizeStandbyConfirm] = useState(false);
  const { runAction, loadingAction, error, clearError } = useWorkflow(viaje.id_viaje, onSuccess);
  const pendingStandbyRequest = useMemo(() => getPendingStandbyRequest(viaje), [viaje]);
  const hasPendingStandbyRequest = pendingStandbyRequest !== null;
  const hasInicioCarga = useMemo(
    () => viaje.eventos_operativos.some((evento) => evento.tipo_evento === "INICIO_CARGA"),
    [viaje.eventos_operativos]
  );
  const hasInicioViaje = useMemo(
    () => viaje.eventos_operativos.some((evento) => evento.tipo_evento === "INICIO_VIAJE"),
    [viaje.eventos_operativos]
  );
  const canReiniciarViaje = viaje.requiere_reinicio_viaje;
  const visibleActions = useMemo(() => {
    if (canReiniciarViaje) {
      return actions.filter((action) => action.key === "reiniciar-viaje");
    }

    return actions.filter((action) => {
      if (action.key === "reiniciar-viaje") return false;
      if (action.key === "iniciar-carga" && hasInicioCarga) return false;
      if (action.key === "iniciar-viaje" && hasInicioViaje) return false;
      return true;
    });
  }, [canReiniciarViaje, hasInicioCarga, hasInicioViaje]);

  const title = useMemo(
    () => `Acciones sobre ${viaje.folio}`,
    [viaje.folio]
  );

  async function handleAuthorizeStandby() {
    clearError();
    const success = await runAction("autorizar-standby");
    if (success) {
      setShowAuthorizeStandbyConfirm(false);
    }
  }

  async function handleAction(action: ActionOption) {
    clearError();

    if (action.key === "finalizar") {
      const confirmed = window.confirm(`¿Seguro que deseas ${action.label.toLowerCase()}?`);
      if (!confirmed) return;
    }

    const payload = buildActionPayload(action);
    if (!payload) return;
    await runAction(action.key, payload);
  }

  function buildActionPayload(action: ActionOption): WorkflowActionPayload | null {
    const trimmedUbicacion = ubicacion.trim();
    const trimmedComentario = comentario.trim();

    if (!trimmedUbicacion) {
      window.alert("La ubicación es obligatoria para esta acción.");
      return null;
    }

    if (action.requiresComment && !trimmedComentario) {
      window.alert("El comentario es obligatorio para esta acción.");
      return null;
    }

    if (!latitud.trim() || !longitud.trim()) {
      window.alert("Debes permitir ubicación para continuar.");
      return null;
    }

    if (!Number.isFinite(Number(latitud)) || !Number.isFinite(Number(longitud))) {
      window.alert("Latitud y longitud deben ser valores numéricos válidos.");
      return null;
    }

    const basePayload: WorkflowActionPayload = {
      ubicacion: trimmedUbicacion,
      latitud: latitud.trim() ? Number(latitud) : null,
      longitud: longitud.trim() ? Number(longitud) : null,
      comentario: trimmedComentario || null
    };

    if (!action.requiresKilometraje && !action.requiresDiesel) {
      return basePayload;
    }

    const parsedKilometraje = Number(kilometraje);
    const parsedNivelDiesel = Number(nivelDiesel);

    if (!Number.isFinite(parsedKilometraje) || parsedKilometraje < 0) {
      window.alert("Captura un kilometraje válido mayor o igual a 0.");
      return null;
    }

    if (!Number.isFinite(parsedNivelDiesel) || parsedNivelDiesel < 0 || parsedNivelDiesel > 100) {
      window.alert("Captura un nivel de diésel entre 0 y 100.");
      return null;
    }

    return {
      ...basePayload,
      kilometraje: parsedKilometraje,
      nivel_diesel: parsedNivelDiesel
    } satisfies WorkflowOperationalPayload;
  }

  const helperText =
    "Iniciar carga y marcar retraso ahora también registran ubicación. La autorización de standby se revisa aparte y no pide nuevos datos operativos."

  return (
    <Card className="p-5 md:p-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
        <p className="text-sm text-slate-600">
          Ejecuta acciones del workflow. El backend validará permisos, transiciones y reglas de negocio.
        </p>
      </div>

      <div className="mt-4 rounded-2xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-800">
        {helperText}
      </div>

      {!isStandby ? (
        <>
          <div className="mt-5">
            <Textarea
              label="Comentario"
              onChange={(event) => {
                clearError();
                setComentario(event.target.value);
              }}
              placeholder="Agrega contexto para la acción si hace falta"
              value={comentario}
            />
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <Input
              label="Kilometraje (para iniciar viaje / standby / finalizar)"
              min="0"
              onChange={(event) => setKilometraje(event.target.value)}
              type="number"
              value={kilometraje}
            />
            <Input
              label="Nivel de diésel (%)"
              max="100"
              min="0"
              onChange={(event) => setNivelDiesel(event.target.value)}
              type="number"
              value={nivelDiesel}
            />
            <Input
              label="Ubicación"
              onChange={(event) => setUbicacion(event.target.value)}
              value={ubicacion}
            />
            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Latitud"
                onChange={(event) => setLatitud(event.target.value)}
                type="number"
                value={latitud}
              />
              <Input
                label="Longitud"
                onChange={(event) => setLongitud(event.target.value)}
                type="number"
                value={longitud}
              />
            </div>
          </div>
        </>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {hasPendingStandbyRequest ? (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          El operador solicitó poner este viaje en standby. Puedes autorizarlo desde aquí.
        </div>
      ) : null}

      {showAuthorizeStandbyConfirm && pendingStandbyRequest ? (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">El operador solicitó poner el viaje en standby.</p>
          <div className="mt-3 space-y-2">
            <p>
              <span className="font-medium">Fecha de solicitud:</span>{" "}
              {new Date(pendingStandbyRequest.created_at).toLocaleString("es-MX")}
            </p>
            <p>
              <span className="font-medium">Ubicación:</span> {pendingStandbyRequest.ubicacion}
            </p>
            <p>
              <span className="font-medium">Comentario:</span>{" "}
              {pendingStandbyRequest.comentario ?? "Sin comentario"}
            </p>
            <p>
              <span className="font-medium">Kilometraje:</span>{" "}
              {pendingStandbyRequest.kilometraje ?? "Sin dato"} ·{" "}
              <span className="font-medium">Diésel:</span>{" "}
              {pendingStandbyRequest.nivel_diesel ?? "Sin dato"}
            </p>
            <p>
              <span className="font-medium">Evidencias:</span>{" "}
              {pendingStandbyRequest.evidencias.length > 0
                ? `${pendingStandbyRequest.evidencias.length} registradas`
                : "Sin evidencias"}
            </p>
            {pendingStandbyRequest.evidencias.length > 0 ? (
              <Link className="font-medium text-brand-700 underline" href="#eventos-operativos">
                Ver evidencias en eventos operativos
              </Link>
            ) : null}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              disabled={loadingAction !== null}
              onClick={() => setShowAuthorizeStandbyConfirm(false)}
              type="button"
              variant="ghost"
            >
              Cancelar
            </Button>
            <Button
              disabled={loadingAction !== null}
              onClick={() => void handleAuthorizeStandby()}
              type="button"
              variant="warning"
            >
              {loadingAction === "autorizar-standby" ? "Procesando..." : "Autorizar standby"}
            </Button>
          </div>
        </div>
      ) : null}

      {isFinalizado ? (
        <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Viaje finalizado. Ya no admite nuevas acciones operativas.
        </div>
      ) : null}

      {canReiniciarViaje ? (
        <div className="mt-4 rounded-2xl border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          Este viaje fue reasignado después de standby. Debe continuar con la acción Reiniciar viaje.
        </div>
      ) : null}

      {isFinalizado ? null : (
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {visibleActions.map((action) => (
            <Button
              key={action.key}
              disabled={loadingAction !== null}
              onClick={() => void handleAction(action)}
              size="lg"
              type="button"
              variant={action.variant}
            >
              {loadingAction === action.key ? "Procesando..." : action.label}
            </Button>
          ))}
          {hasPendingStandbyRequest ? (
            <Button
              disabled={loadingAction !== null}
              onClick={() => setShowAuthorizeStandbyConfirm(true)}
              size="lg"
              type="button"
              variant="warning"
            >
              Revisar solicitud de standby
            </Button>
          ) : null}
        </div>
      )}

      <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
        Evidencias, documentos y eventos operativos quedan consolidados en el detalle del viaje.
      </div>
    </Card>
  );
}
