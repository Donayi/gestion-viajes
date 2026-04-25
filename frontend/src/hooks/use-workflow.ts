"use client";

import { useState } from "react";

import { ApiError } from "@/services/api-client";
import {
  finalizarViajeRequest,
  iniciarCargaRequest,
  iniciarViajeRequest,
  marcarRetrasoRequest,
  ponerStandbyRequest
} from "@/services/workflow.service";
import type { ViajeComentarioAccion, WorkflowOperationalPayload } from "@/types/viaje";

type ActionType =
  | "iniciar-carga"
  | "iniciar-viaje"
  | "marcar-retraso"
  | "poner-standby"
  | "finalizar";

const actionMap = {
  "iniciar-carga": iniciarCargaRequest,
  "iniciar-viaje": iniciarViajeRequest,
  "marcar-retraso": marcarRetrasoRequest,
  "poner-standby": ponerStandbyRequest,
  finalizar: finalizarViajeRequest
} as const;

export function useWorkflow(viajeId: number, onSuccess: () => Promise<void> | void) {
  const [loadingAction, setLoadingAction] = useState<ActionType | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAction(
    action: ActionType,
    payload: ViajeComentarioAccion | WorkflowOperationalPayload
  ) {
    setLoadingAction(action);
    setError(null);

    try {
      const request = actionMap[action] as (
        currentViajeId: number,
        currentPayload: ViajeComentarioAccion | WorkflowOperationalPayload
      ) => Promise<unknown>;
      await request(viajeId, payload);
      await onSuccess();
      return true;
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "No fue posible ejecutar la accion";
      setError(message);
      return false;
    } finally {
      setLoadingAction(null);
    }
  }

  return { runAction, loadingAction, error, clearError: () => setError(null) };
}
