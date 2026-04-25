"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useWorkflow } from "@/hooks/use-workflow";
import type { ViajeComentarioAccion, ViajeDetail, WorkflowOperationalPayload } from "@/types/viaje";

type WorkflowActionKey =
  | "iniciar-carga"
  | "iniciar-viaje"
  | "marcar-retraso"
  | "poner-standby"
  | "finalizar";

type OperatorAction = {
  key: WorkflowActionKey;
  label: string;
  variant: "primary" | "secondary" | "ghost" | "danger";
  confirm?: boolean;
  requiresOperationalData?: boolean;
};

type OperationalFormState = {
  kilometraje: string;
  nivel_diesel: string;
  ubicacion: string;
  latitud: string;
  longitud: string;
  comentario: string;
};

const actions: OperatorAction[] = [
  { key: "iniciar-carga", label: "Iniciar carga", variant: "primary" },
  {
    key: "iniciar-viaje",
    label: "Iniciar viaje",
    variant: "primary",
    requiresOperationalData: true
  },
  { key: "marcar-retraso", label: "Marcar retraso", variant: "secondary" },
  {
    key: "poner-standby",
    label: "Poner standby",
    variant: "secondary",
    confirm: true,
    requiresOperationalData: true
  },
  {
    key: "finalizar",
    label: "Finalizar",
    variant: "danger",
    confirm: true,
    requiresOperationalData: true
  }
];

const initialOperationalForm: OperationalFormState = {
  kilometraje: "",
  nivel_diesel: "",
  ubicacion: "",
  latitud: "",
  longitud: "",
  comentario: ""
};

export function OperatorActionPanel({
  viaje,
  onSuccess
}: {
  viaje: ViajeDetail;
  onSuccess: () => Promise<void>;
}) {
  const [comentarioRapido, setComentarioRapido] = useState("");
  const [activeAction, setActiveAction] = useState<OperatorAction | null>(null);
  const [operationalForm, setOperationalForm] =
    useState<OperationalFormState>(initialOperationalForm);
  const [geoLoading, setGeoLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const { runAction, loadingAction, error, clearError } = useWorkflow(viaje.id_viaje, onSuccess);

  const currentError = localError ?? error;
  const activeActionLabel = activeAction?.label ?? "";

  const actionTitle = useMemo(() => {
    if (!activeAction) return "Captura operativa";
    return `${activeAction.label}: datos operativos`;
  }, [activeAction]);

  function updateOperationalField(field: keyof OperationalFormState, value: string) {
    setOperationalForm((current) => ({ ...current, [field]: value }));
  }

  function openOperationalSheet(action: OperatorAction) {
    clearError();
    setLocalError(null);
    setOperationalForm((current) => ({
      ...initialOperationalForm,
      comentario: current.comentario || comentarioRapido
    }));
    setActiveAction(action);
  }

  function closeOperationalSheet() {
    if (loadingAction) return;
    setActiveAction(null);
    setLocalError(null);
    clearError();
  }

  async function handleQuickAction(action: OperatorAction) {
    clearError();
    setLocalError(null);

    if (action.requiresOperationalData) {
      openOperationalSheet(action);
      return;
    }

    if (action.confirm) {
      const confirmed = window.confirm(`¿Seguro que deseas ${action.label.toLowerCase()}?`);
      if (!confirmed) return;
    }

    const payload: ViajeComentarioAccion = { comentario: comentarioRapido || null };
    await runAction(action.key, payload);
  }

  function buildOperationalPayload(): WorkflowOperationalPayload | null {
    const kilometraje = Number(operationalForm.kilometraje);
    const nivelDiesel = Number(operationalForm.nivel_diesel);
    const ubicacion = operationalForm.ubicacion.trim();
    const latitud = operationalForm.latitud.trim();
    const longitud = operationalForm.longitud.trim();

    if (!ubicacion) {
      setLocalError("La ubicación es obligatoria para esta acción.");
      return null;
    }

    if (!Number.isFinite(kilometraje) || kilometraje < 0) {
      setLocalError("El kilometraje debe ser mayor o igual a 0.");
      return null;
    }

    if (!Number.isFinite(nivelDiesel) || nivelDiesel < 0 || nivelDiesel > 100) {
      setLocalError("El nivel de diésel debe estar entre 0 y 100.");
      return null;
    }

    if ((latitud && !longitud) || (!latitud && longitud)) {
      setLocalError("Latitud y longitud deben enviarse juntas.");
      return null;
    }

    const payload: WorkflowOperationalPayload = {
      kilometraje,
      nivel_diesel: nivelDiesel,
      ubicacion,
      comentario: operationalForm.comentario.trim() || null
    };

    if (latitud && longitud) {
      payload.latitud = Number(latitud);
      payload.longitud = Number(longitud);
    }

    return payload;
  }

  async function handleOperationalSubmit() {
    if (!activeAction) return;

    clearError();
    setLocalError(null);

    if (activeAction.confirm) {
      const confirmed = window.confirm(`¿Seguro que deseas ${activeAction.label.toLowerCase()}?`);
      if (!confirmed) return;
    }

    const payload = buildOperationalPayload();
    if (!payload) return;

    const success = await runAction(activeAction.key, payload);
    if (success) {
      setComentarioRapido("");
      setActiveAction(null);
      setOperationalForm(initialOperationalForm);
    }
  }

  async function useCurrentLocation() {
    if (!navigator.geolocation) {
      setLocalError("Tu navegador no permite obtener la ubicación actual.");
      return;
    }

    setGeoLoading(true);
    setLocalError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        updateOperationalField("latitud", position.coords.latitude.toFixed(7));
        updateOperationalField("longitud", position.coords.longitude.toFixed(7));
        setGeoLoading(false);
      },
      () => {
        setLocalError("No fue posible obtener tu ubicación actual.");
        setGeoLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  return (
    <>
      <section className="rounded-[2rem] border border-white/10 bg-white p-5 shadow-soft">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
            Acciones rápidas
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">Control del viaje</h2>
        </div>

        <div className="mt-5">
          <Textarea
            label="Comentario rápido"
            onChange={(event) => setComentarioRapido(event.target.value)}
            placeholder="Úsalo para carga o retraso"
            value={comentarioRapido}
          />
        </div>

        {currentError ? (
          <div className="mt-4 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {currentError}
          </div>
        ) : null}

        <div className="mt-5 grid gap-3">
          {actions.map((action) => (
            <Button
              key={action.key}
              className="min-h-14 rounded-[1.25rem] text-base font-semibold"
              disabled={loadingAction !== null}
              onClick={() => void handleQuickAction(action)}
              type="button"
              variant={action.variant}
            >
              {loadingAction === action.key ? "Procesando..." : action.label}
            </Button>
          ))}
        </div>
      </section>

      {activeAction ? (
        <div className="fixed inset-0 z-50 flex items-end bg-slate-950/45 backdrop-blur-sm">
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-[2rem] bg-white px-5 pb-8 pt-5 shadow-2xl md:mx-auto md:max-w-xl md:rounded-[2rem] md:mb-6">
            <div className="mx-auto h-1.5 w-14 rounded-full bg-slate-200 md:hidden" />

            <div className="mt-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
                  Captura operativa
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">{actionTitle}</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Registra el estado operativo antes de continuar con el flujo.
                </p>
              </div>
              <Button onClick={closeOperationalSheet} type="button" variant="ghost">
                Cerrar
              </Button>
            </div>

            <div className="mt-6 grid gap-4">
              <Input
                inputMode="decimal"
                label="Kilometraje actual"
                min="0"
                onChange={(event) => updateOperationalField("kilometraje", event.target.value)}
                placeholder="Ej. 125430"
                type="number"
                value={operationalForm.kilometraje}
              />
              <Input
                inputMode="decimal"
                label="Nivel de diésel (%)"
                max="100"
                min="0"
                onChange={(event) => updateOperationalField("nivel_diesel", event.target.value)}
                placeholder="Ej. 78"
                type="number"
                value={operationalForm.nivel_diesel}
              />
              <Input
                label="Ubicación"
                onChange={(event) => updateOperationalField("ubicacion", event.target.value)}
                placeholder="Ej. Patio Monterrey"
                value={operationalForm.ubicacion}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  inputMode="decimal"
                  label="Latitud (opcional)"
                  onChange={(event) => updateOperationalField("latitud", event.target.value)}
                  placeholder="Ej. 25.6866000"
                  type="number"
                  value={operationalForm.latitud}
                />
                <Input
                  inputMode="decimal"
                  label="Longitud (opcional)"
                  onChange={(event) => updateOperationalField("longitud", event.target.value)}
                  placeholder="Ej. -100.3161000"
                  type="number"
                  value={operationalForm.longitud}
                />
              </div>

              <Button
                className="min-h-12 rounded-[1.25rem]"
                disabled={geoLoading || loadingAction !== null}
                onClick={() => void useCurrentLocation()}
                type="button"
                variant="secondary"
              >
                {geoLoading ? "Obteniendo ubicación..." : "Usar ubicación actual"}
              </Button>

              <Textarea
                label="Comentario (opcional)"
                onChange={(event) => updateOperationalField("comentario", event.target.value)}
                placeholder={`Agrega contexto para ${activeActionLabel.toLowerCase()}`}
                value={operationalForm.comentario}
              />
            </div>

            {currentError ? (
              <div className="mt-4 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {currentError}
              </div>
            ) : null}

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <Button
                className="min-h-14 rounded-[1.25rem] text-base font-semibold"
                disabled={loadingAction !== null}
                onClick={closeOperationalSheet}
                type="button"
                variant="ghost"
              >
                Cancelar
              </Button>
              <Button
                className="min-h-14 rounded-[1.25rem] text-base font-semibold"
                disabled={loadingAction !== null}
                onClick={() => void handleOperationalSubmit()}
                type="button"
                variant={activeAction.variant}
              >
                {loadingAction === activeAction.key ? "Procesando..." : activeAction.label}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
