"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useWorkflow } from "@/hooks/use-workflow";
import type { ViajeDetail, WorkflowOperationalPayload } from "@/types/viaje";

type ActionOption = {
  key: "iniciar-carga" | "iniciar-viaje" | "marcar-retraso" | "poner-standby" | "finalizar";
  label: string;
};

const actions: ActionOption[] = [
  { key: "iniciar-carga", label: "Iniciar carga" },
  { key: "iniciar-viaje", label: "Iniciar viaje" },
  { key: "marcar-retraso", label: "Marcar retraso" },
  { key: "poner-standby", label: "Poner standby" },
  { key: "finalizar", label: "Finalizar" }
];

export function WorkflowActions({
  viaje,
  onSuccess
}: {
  viaje: ViajeDetail;
  onSuccess: () => Promise<void>;
}) {
  const [comentario, setComentario] = useState("");
  const [kilometraje, setKilometraje] = useState("");
  const [nivelDiesel, setNivelDiesel] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [latitud, setLatitud] = useState("");
  const [longitud, setLongitud] = useState("");
  const { runAction, loadingAction, error, clearError } = useWorkflow(viaje.id_viaje, onSuccess);

  const title = useMemo(
    () => `Acciones sobre ${viaje.folio}`,
    [viaje.folio]
  );

  async function handleAction(action: ActionOption) {
    clearError();

    if (action.key === "finalizar" || action.key === "poner-standby") {
      const confirmed = window.confirm(`¿Seguro que deseas ${action.label.toLowerCase()}?`);
      if (!confirmed) return;
    }

    if (action.key === "iniciar-viaje" || action.key === "poner-standby" || action.key === "finalizar") {
      const payload = buildOperationalPayload();
      if (!payload) return;
      await runAction(action.key, payload);
      return;
    }

    await runAction(action.key, { comentario: comentario || null });
  }

  function buildOperationalPayload(): WorkflowOperationalPayload | null {
    const parsedKilometraje = Number(kilometraje);
    const parsedNivelDiesel = Number(nivelDiesel);
    const trimmedUbicacion = ubicacion.trim();

    if (!Number.isFinite(parsedKilometraje) || parsedKilometraje < 0) {
      window.alert("Captura un kilometraje válido mayor o igual a 0.");
      return null;
    }

    if (!Number.isFinite(parsedNivelDiesel) || parsedNivelDiesel < 0 || parsedNivelDiesel > 100) {
      window.alert("Captura un nivel de diésel entre 0 y 100.");
      return null;
    }

    if (!trimmedUbicacion) {
      window.alert("La ubicación es obligatoria para esta acción.");
      return null;
    }

    if ((latitud.trim() && !longitud.trim()) || (!latitud.trim() && longitud.trim())) {
      window.alert("Latitud y longitud deben enviarse juntas.");
      return null;
    }

    return {
      kilometraje: parsedKilometraje,
      nivel_diesel: parsedNivelDiesel,
      ubicacion: trimmedUbicacion,
      latitud: latitud.trim() ? Number(latitud) : null,
      longitud: longitud.trim() ? Number(longitud) : null,
      comentario: comentario || null
    };
  }

  return (
    <Card className="p-5 md:p-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
        <p className="text-sm text-slate-600">
          Ejecuta acciones del workflow. El backend validara permisos, transiciones y reglas de negocio.
        </p>
      </div>

      <div className="mt-5">
        <Textarea
          label="Comentario opcional"
          onChange={(event) => {
            clearError();
            setComentario(event.target.value);
          }}
          placeholder="Agrega contexto para la accion si hace falta"
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

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {actions.map((action) => (
          <Button
            key={action.key}
            disabled={loadingAction !== null}
            onClick={() => void handleAction(action)}
            type="button"
            variant={action.key === "finalizar" ? "danger" : "primary"}
          >
            {loadingAction === action.key ? "Procesando..." : action.label}
          </Button>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
        Evidencias y documentos quedan visibles como siguiente etapa. Esta primera version se enfoca en auth, consulta y workflow basico.
      </div>
    </Card>
  );
}
