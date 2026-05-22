"use client";

import { useState } from "react";

import { ApiError } from "@/services/api-client";
import {
  autorizarStandbyRequest,
  finalizarViajeRequest,
  iniciarCargaRequest,
  iniciarViajeRequest,
  marcarRetrasoRequest,
  ponerStandbyRequest,
  reiniciarViajeRequest,
  solicitarStandbyRequest
} from "@/services/workflow.service";
import type { WorkflowActionPayload } from "@/types/viaje";

type ActionType =
  | "iniciar-carga"
  | "iniciar-viaje"
  | "reiniciar-viaje"
  | "marcar-retraso"
  | "poner-standby"
  | "solicitar-standby"
  | "autorizar-standby"
  | "finalizar";

const actionMap = {
  "iniciar-carga": iniciarCargaRequest,
  "iniciar-viaje": iniciarViajeRequest,
  "reiniciar-viaje": reiniciarViajeRequest,
  "marcar-retraso": marcarRetrasoRequest,
  "poner-standby": ponerStandbyRequest,
  "solicitar-standby": solicitarStandbyRequest,
  "autorizar-standby": autorizarStandbyRequest,
  finalizar: finalizarViajeRequest
} as const;

export function useWorkflow(viajeId: number, onSuccess: () => Promise<void> | void) {
  const [loadingAction, setLoadingAction] = useState<ActionType | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAction(
    action: ActionType,
    payload?: WorkflowActionPayload
  ) {
    setLoadingAction(action);
    setError(null);

    try {
      const request = actionMap[action] as (
        currentViajeId: number,
        currentPayload?: WorkflowActionPayload
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
