"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useWorkflow } from "@/hooks/use-workflow";
import type { ViajeDetail } from "@/types/viaje";

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
};

const actions: OperatorAction[] = [
  { key: "iniciar-carga", label: "Iniciar carga", variant: "primary" as const },
  { key: "iniciar-viaje", label: "Iniciar viaje", variant: "primary" as const },
  { key: "marcar-retraso", label: "Marcar retraso", variant: "secondary" as const },
  { key: "poner-standby", label: "Poner standby", variant: "secondary" as const, confirm: true },
  { key: "finalizar", label: "Finalizar", variant: "danger" as const, confirm: true }
];

export function OperatorActionPanel({
  viaje,
  onSuccess
}: {
  viaje: ViajeDetail;
  onSuccess: () => Promise<void>;
}) {
  const [comentario, setComentario] = useState("");
  const { runAction, loadingAction, error, clearError } = useWorkflow(viaje.id_viaje, onSuccess);

  async function handleAction(action: OperatorAction) {
    clearError();

    if (action.confirm) {
      const confirmed = window.confirm(`¿Seguro que deseas ${action.label.toLowerCase()}?`);
      if (!confirmed) return;
    }

    await runAction(action.key, comentario);
  }

  return (
    <section className="rounded-[2rem] border border-white/10 bg-white p-5 shadow-soft">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
          Acciones rápidas
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-950">Control del viaje</h2>
      </div>

      <div className="mt-5">
        <Textarea
          label="Comentario"
          onChange={(event) => setComentario(event.target.value)}
          placeholder="Agrega contexto si es necesario"
          value={comentario}
        />
      </div>

      {error ? (
        <div className="mt-4 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="mt-5 grid gap-3">
        {actions.map((action) => (
          <Button
            key={action.key}
            className="min-h-14 rounded-[1.25rem] text-base font-semibold"
            disabled={loadingAction !== null}
            onClick={() => void handleAction(action)}
            type="button"
            variant={action.variant}
          >
            {loadingAction === action.key ? "Procesando..." : action.label}
          </Button>
        ))}
      </div>
    </section>
  );
}
