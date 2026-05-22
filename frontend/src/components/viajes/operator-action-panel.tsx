"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { getPendingStandbyRequest } from "@/components/viajes/workflow-helpers";
import {
  getEvidenciasByViajeRequest,
  getPresignedUrlRequest,
  getTiposEvidenciaRequest,
  uploadFileToR2,
} from "@/services/evidencias.service";
import { useWorkflow } from "@/hooks/use-workflow";
import { ApiError } from "@/services/api-client";
import type { EvidenciaResponse, TipoEvidencia } from "@/types/evidencia";
import type {
  EvidenciaOperativaInput,
  ViajeDetail,
  WorkflowActionPayload,
  WorkflowLocationPayload,
  WorkflowOperationalPayload
} from "@/types/viaje";

type WorkflowActionKey =
  | "iniciar-carga"
  | "iniciar-viaje"
  | "reiniciar-viaje"
  | "marcar-retraso"
  | "solicitar-standby"
  | "finalizar";

type OperatorAction = {
  key: WorkflowActionKey;
  label: string;
  variant: "primary" | "secondary" | "warning" | "ghost" | "danger" | "success";
  confirm?: boolean;
  requiresKilometraje?: boolean;
  requiresDiesel?: boolean;
  requiresComment?: boolean;
  requiresEvidence?: boolean;
  helperText: string;
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
  {
    key: "iniciar-carga",
    label: "Iniciar carga",
    variant: "secondary",
    helperText: "Captura ubicación actual antes de marcar el inicio de carga."
  },
  {
    key: "iniciar-viaje",
    label: "Iniciar viaje",
    variant: "primary",
    requiresKilometraje: true,
    requiresDiesel: true,
    requiresEvidence: true,
    helperText: "Registra kilometraje, diésel y ubicación de salida."
  },
  {
    key: "reiniciar-viaje",
    label: "Reiniciar viaje",
    variant: "warning",
    requiresKilometraje: true,
    requiresDiesel: true,
    helperText: "Continúa el viaje reasignado después de standby con una nueva captura operativa."
  },
  {
    key: "marcar-retraso",
    label: "Marcar retraso",
    variant: "warning",
    requiresComment: true,
    helperText: "Explica el motivo del retraso y registra tu ubicación."
  },
  {
    key: "solicitar-standby",
    label: "Solicitar standby",
    variant: "warning",
    requiresKilometraje: true,
    requiresDiesel: true,
    requiresComment: true,
    helperText: "Registra el estado operativo actual para enviar la solicitud de standby a administración."
  },
  {
    key: "finalizar",
    label: "Finalizar",
    variant: "success",
    confirm: true,
    requiresKilometraje: true,
    requiresDiesel: true,
    requiresEvidence: true,
    helperText: "Captura los datos finales del viaje antes de cerrarlo."
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

type ActionEvidenceDraft = {
  idTipoEvidencia: string;
  comentario: string;
  file: File | null;
};

type ActionEvidenceItem = {
  tempId: string;
  nombreArchivo: string;
  data: EvidenciaOperativaInput;
};

const initialEvidenceDraft: ActionEvidenceDraft = {
  idTipoEvidencia: "",
  comentario: "",
  file: null,
};

export function OperatorActionPanel({
  viaje,
  onSuccess
}: {
  viaje: ViajeDetail;
  onSuccess: () => Promise<void>;
}) {
  const estatusActual = viaje.estatus_actual.clave;
  const isFinalizado = estatusActual === "FINALIZADO";
  const isCancelado = estatusActual === "CANCELADO";
  const isReadOnly = isFinalizado || isCancelado;
  const isStandby = viaje.estatus_actual.clave === "STANDBY";
  const hasInicioCarga = useMemo(
    () => viaje.eventos_operativos.some((evento) => evento.tipo_evento === "INICIO_CARGA"),
    [viaje.eventos_operativos]
  );
  const hasInicioViaje = useMemo(
    () => viaje.eventos_operativos.some((evento) => evento.tipo_evento === "INICIO_VIAJE"),
    [viaje.eventos_operativos]
  );
  const canReiniciarViaje = viaje.requiere_reinicio_viaje;
  const hasPendingStandbyRequest = useMemo(() => getPendingStandbyRequest(viaje) !== null, [viaje]);
  const visibleActions = useMemo(() => {
    if (isReadOnly || isStandby) {
      return [];
    }

    if (canReiniciarViaje) {
      return actions.filter((action) => action.key === "reiniciar-viaje");
    }

    switch (estatusActual) {
      case "ASIGNADO":
        return actions.filter((action) => action.key === "iniciar-carga" && !hasInicioCarga);
      case "CARGANDO":
        return actions.filter((action) => action.key === "iniciar-viaje" && !hasInicioViaje);
      case "INICIADO":
        return actions.filter((action) =>
          ["marcar-retraso", "solicitar-standby", "finalizar"].includes(action.key)
        );
      case "RETRASADO":
        return actions.filter((action) =>
          ["solicitar-standby", "finalizar"].includes(action.key)
        );
      default:
        return [];
    }
  }, [canReiniciarViaje, estatusActual, hasInicioCarga, hasInicioViaje, isReadOnly, isStandby]);
  const [activeAction, setActiveAction] = useState<OperatorAction | null>(null);
  const [operationalForm, setOperationalForm] = useState<OperationalFormState>(initialOperationalForm);
  const [geoLoading, setGeoLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [geoMessage, setGeoMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [tiposEvidencia, setTiposEvidencia] = useState<TipoEvidencia[]>([]);
  const [loadingTiposEvidencia, setLoadingTiposEvidencia] = useState(false);
  const [existingEvidencias, setExistingEvidencias] = useState<EvidenciaResponse[]>([]);
  const [loadingExistingEvidencias, setLoadingExistingEvidencias] = useState(false);
  const [actionEvidenceDraft, setActionEvidenceDraft] = useState<ActionEvidenceDraft>(initialEvidenceDraft);
  const [actionEvidences, setActionEvidences] = useState<ActionEvidenceItem[]>([]);
  const [uploadingEvidence, setUploadingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const { runAction, loadingAction, error, clearError } = useWorkflow(viaje.id_viaje, onSuccess);

  const currentError = localError ?? error;

  const validationError = useMemo(() => {
    if (!activeAction) return null;

    const ubicacion = operationalForm.ubicacion.trim();
    const comentario = operationalForm.comentario.trim();
    const latitud = operationalForm.latitud.trim();
    const longitud = operationalForm.longitud.trim();

    if (!ubicacion) {
      return "La ubicación es obligatoria para esta acción.";
    }

    if (!latitud || !longitud) {
      return "Debes permitir ubicación para continuar.";
    }

    if (!Number.isFinite(Number(latitud)) || !Number.isFinite(Number(longitud))) {
      return "Latitud y longitud deben ser valores numéricos válidos.";
    }

    if (activeAction.requiresKilometraje) {
      const kilometraje = Number(operationalForm.kilometraje);
      if (!Number.isFinite(kilometraje) || kilometraje < 0) {
        return "El kilometraje debe ser mayor o igual a 0.";
      }
    }

    if (activeAction.requiresDiesel) {
      const nivelDiesel = Number(operationalForm.nivel_diesel);
      if (!Number.isFinite(nivelDiesel) || nivelDiesel < 0 || nivelDiesel > 100) {
        return "El nivel de diésel debe estar entre 0 y 100.";
      }
    }

    if (activeAction.requiresComment && !comentario) {
      return "El comentario es obligatorio para esta acción.";
    }

    if (activeAction.requiresEvidence && actionEvidences.length === 0 && existingEvidencias.length === 0) {
      return "Esta acción requiere al menos una evidencia nueva o una evidencia válida ya asociada al viaje.";
    }

    return null;
  }, [actionEvidences.length, activeAction, existingEvidencias.length, operationalForm]);

  const submitDisabled = useMemo(() => {
    if (!activeAction) return true;
    if (loadingAction !== null || geoLoading || uploadingEvidence) return true;
    return validationError !== null;
  }, [activeAction, geoLoading, loadingAction, uploadingEvidence, validationError]);

  function updateOperationalField(field: keyof OperationalFormState, value: string) {
    setOperationalForm((current) => ({ ...current, [field]: value }));
    setLocalError(null);
    clearError();
  }

  function openOperationalSheet(action: OperatorAction) {
    clearError();
    setLocalError(null);
    setGeoMessage(null);
    setSuccessMessage(null);
    setEvidenceError(null);
    setOperationalForm(initialOperationalForm);
    setActionEvidenceDraft(initialEvidenceDraft);
    setActionEvidences([]);
    setActiveAction(action);
  }

  function closeOperationalSheet() {
    if (loadingAction) return;
    setActiveAction(null);
    setLocalError(null);
    setGeoMessage(null);
    setEvidenceError(null);
    clearError();
  }

  function buildActionPayload(action: OperatorAction): WorkflowActionPayload | null {
    if (validationError) {
      setLocalError(validationError);
      return null;
    }

    const basePayload: WorkflowLocationPayload = {
      ubicacion: operationalForm.ubicacion.trim(),
      comentario: operationalForm.comentario.trim() || null
    };

    const latitud = operationalForm.latitud.trim();
    const longitud = operationalForm.longitud.trim();
    if (latitud && longitud) {
      basePayload.latitud = Number(latitud);
      basePayload.longitud = Number(longitud);
    }

    if (action.requiresKilometraje || action.requiresDiesel) {
      return {
        ...basePayload,
        evidencias: actionEvidences.map((item) => item.data),
        kilometraje: Number(operationalForm.kilometraje),
        nivel_diesel: Number(operationalForm.nivel_diesel)
      } satisfies WorkflowOperationalPayload;
    }

    return {
      ...basePayload,
      evidencias: actionEvidences.map((item) => item.data),
    };
  }

  async function handleActionSubmit() {
    if (!activeAction) return;

    clearError();
    setLocalError(null);
    setSuccessMessage(null);

    if (activeAction.confirm) {
      const confirmed = window.confirm(`¿Seguro que deseas ${activeAction.label.toLowerCase()}?`);
      if (!confirmed) return;
    }

    const payload = buildActionPayload(activeAction);
    if (!payload) return;

    const success = await runAction(activeAction.key, payload);
    if (success) {
      setSuccessMessage(
        activeAction.key === "solicitar-standby"
          ? "Solicitud enviada. Pendiente de autorización administrativa."
          : `${activeAction.label} ejecutado correctamente.`
      );
      setActiveAction(null);
      setOperationalForm(initialOperationalForm);
      setGeoMessage(null);
    }
  }

  async function loadEvidenceContext() {
    setLoadingTiposEvidencia(true);
    setLoadingExistingEvidencias(true);
    setEvidenceError(null);

    try {
      const [tipos, evidencias] = await Promise.all([
        getTiposEvidenciaRequest(),
        getEvidenciasByViajeRequest(viaje.id_viaje),
      ]);
      setTiposEvidencia(tipos);
      setExistingEvidencias(evidencias);
      setActionEvidenceDraft((current) => ({
        ...current,
        idTipoEvidencia: current.idTipoEvidencia || String(tipos[0]?.id_tipo_evidencia ?? ""),
      }));
    } catch (currentError) {
      setEvidenceError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible preparar la sección de evidencias para esta acción."
      );
    } finally {
      setLoadingTiposEvidencia(false);
      setLoadingExistingEvidencias(false);
    }
  }

  async function handleAddEvidence() {
    if (!actionEvidenceDraft.file) {
      setEvidenceError("Selecciona un archivo antes de agregar evidencia.");
      return;
    }

    if (!actionEvidenceDraft.idTipoEvidencia) {
      setEvidenceError("Selecciona un tipo de evidencia.");
      return;
    }

    setUploadingEvidence(true);
    setEvidenceError(null);

    try {
      const presign = await getPresignedUrlRequest({
        filename: actionEvidenceDraft.file.name,
        content_type: actionEvidenceDraft.file.type || "application/octet-stream",
        size_bytes: actionEvidenceDraft.file.size,
      });

      await uploadFileToR2(presign.upload_url, actionEvidenceDraft.file);

      setActionEvidences((current) => [
        ...current,
        {
          tempId: `${Date.now()}-${current.length}`,
          nombreArchivo: actionEvidenceDraft.file?.name ?? "Archivo",
          data: {
            id_tipo_evidencia: Number(actionEvidenceDraft.idTipoEvidencia),
            id_archivo: presign.id_archivo,
            comentario: actionEvidenceDraft.comentario.trim() || null,
            latitud: operationalForm.latitud.trim() ? Number(operationalForm.latitud) : null,
            longitud: operationalForm.longitud.trim() ? Number(operationalForm.longitud) : null,
          },
        },
      ]);

      setActionEvidenceDraft((current) => ({
        idTipoEvidencia: current.idTipoEvidencia,
        comentario: "",
        file: null,
      }));
    } catch (currentError) {
      setEvidenceError(
        currentError instanceof ApiError
          ? currentError.message
          : currentError instanceof Error
            ? currentError.message
            : "No fue posible subir la evidencia para esta acción."
      );
    } finally {
      setUploadingEvidence(false);
    }
  }

  function removeEvidence(tempId: string) {
    setActionEvidences((current) => current.filter((item) => item.tempId !== tempId));
  }

  function captureCurrentLocation(options?: { auto?: boolean }) {
    const auto = options?.auto ?? false;

    if (!navigator.geolocation) {
      setGeoMessage(
        auto
          ? "Debes permitir ubicación para continuar."
          : "Tu navegador no permite obtener la ubicación actual."
      );
      return;
    }

    setGeoLoading(true);
    setLocalError(null);
    setGeoMessage(auto ? "Detectando ubicación automáticamente..." : null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        updateOperationalField("latitud", position.coords.latitude.toFixed(7));
        updateOperationalField("longitud", position.coords.longitude.toFixed(7));
        setOperationalForm((current) => ({
          ...current,
          ubicacion: current.ubicacion.trim() || "Ubicación detectada automáticamente"
        }));
        setGeoMessage("Ubicación detectada correctamente.");
        setGeoLoading(false);
      },
      () => {
        setGeoMessage(
          auto
            ? "Debes permitir ubicación para continuar."
            : "No fue posible obtener tu ubicación actual."
        );
        setGeoLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  useEffect(() => {
    if (!activeAction || activeAction.key !== "finalizar") {
      return;
    }

    void captureCurrentLocation({ auto: true });
  }, [activeAction]);

  useEffect(() => {
    if (!activeAction) {
      return;
    }

    void loadEvidenceContext();
  }, [activeAction]);

  return (
    <>
      <section className="rounded-[2rem] border border-white/10 bg-white p-5 shadow-soft">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
            Acciones rápidas
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">Control del viaje</h2>
          <p className="mt-2 text-sm text-slate-600">
            Cada acción abre una captura rápida para registrar la operación antes de cambiar estatus.
          </p>
        </div>

        {successMessage ? (
          <div className="mt-4 rounded-[1.25rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {successMessage}
          </div>
        ) : null}

        {currentError ? (
          <div className="mt-4 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {currentError}
          </div>
        ) : null}

        {isStandby ? (
          <div className="mt-4 rounded-[1.25rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Viaje en standby, pendiente de reasignación administrativa. No puedes retomarlo desde esta vista.
          </div>
        ) : null}

        {isReadOnly ? (
          <div className="mt-4 rounded-[1.25rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {isCancelado
              ? "Viaje cancelado. Ya no admite nuevas acciones operativas."
              : "Viaje finalizado. Ya no admite nuevas acciones operativas."}
          </div>
        ) : null}

        {hasPendingStandbyRequest ? (
          <div className="mt-4 rounded-[1.25rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Ya existe una solicitud de standby pendiente de autorización administrativa.
          </div>
        ) : null}

        {canReiniciarViaje ? (
          <div className="mt-4 rounded-[1.25rem] border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
            Este viaje ya había iniciado antes del standby. El nuevo operador debe continuarlo con la acción
            &nbsp;<span className="font-semibold">Reiniciar viaje</span>.
          </div>
        ) : null}

        {isReadOnly ? null : (
          <div className="mt-5 grid gap-3">
            {visibleActions.map((action) => (
              <Button
                key={action.key}
                className="min-h-14 rounded-[1.25rem] text-base font-semibold"
                disabled={
                  loadingAction !== null ||
                  isStandby ||
                  (action.key === "solicitar-standby" && hasPendingStandbyRequest)
                }
                onClick={() => openOperationalSheet(action)}
                size="lg"
                type="button"
                variant={action.variant}
              >
                {loadingAction === action.key ? "Procesando..." : action.label}
              </Button>
            ))}
          </div>
        )}

        {!isReadOnly && !isStandby && visibleActions.length === 0 ? (
          <div className="mt-4 rounded-[1.25rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            No hay acciones operativas disponibles para el estatus actual del viaje.
          </div>
        ) : null}
      </section>

      {activeAction ? (
        <div className="fixed inset-0 z-50 flex items-end bg-slate-950/45 backdrop-blur-sm">
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-[2rem] bg-white px-5 pb-8 pt-5 shadow-2xl md:mx-auto md:mb-6 md:max-w-xl md:rounded-[2rem]">
            <div className="mx-auto h-1.5 w-14 rounded-full bg-slate-200 md:hidden" />

            <div className="mt-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
                  Captura operativa
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">{activeAction.label}</h3>
                <p className="mt-2 text-sm text-slate-600">{activeAction.helperText}</p>
              </div>
              <Button onClick={closeOperationalSheet} type="button" variant="ghost">
                Cerrar
              </Button>
            </div>

            <div className="mt-6 grid gap-4">
              {activeAction.requiresKilometraje ? (
                <Input
                  inputMode="decimal"
                  label="Kilometraje actual"
                  min="0"
                  onChange={(event) => updateOperationalField("kilometraje", event.target.value)}
                  placeholder="Ej. 125430"
                  required
                  type="number"
                  value={operationalForm.kilometraje}
                />
              ) : null}

              {activeAction.requiresDiesel ? (
                <Input
                  inputMode="decimal"
                  label="Nivel de diésel (%)"
                  max="100"
                  min="0"
                  onChange={(event) => updateOperationalField("nivel_diesel", event.target.value)}
                  placeholder="Ej. 78"
                  required
                  type="number"
                  value={operationalForm.nivel_diesel}
                />
              ) : null}

              <Input
                label="Ubicación"
                onChange={(event) => updateOperationalField("ubicacion", event.target.value)}
                placeholder="Ej. Patio Monterrey"
                required
                value={operationalForm.ubicacion}
              />

              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  inputMode="decimal"
                  label="Latitud"
                  max="90"
                  min="-90"
                  onChange={(event) => updateOperationalField("latitud", event.target.value)}
                  placeholder="Ej. 25.6866000"
                  required
                  type="number"
                  value={operationalForm.latitud}
                />
                <Input
                  inputMode="decimal"
                  label="Longitud"
                  max="180"
                  min="-180"
                  onChange={(event) => updateOperationalField("longitud", event.target.value)}
                  placeholder="Ej. -100.3161000"
                  required
                  type="number"
                  value={operationalForm.longitud}
                />
              </div>

              <Button
                className="min-h-12 rounded-[1.25rem]"
                disabled={geoLoading || loadingAction !== null}
                onClick={() => void captureCurrentLocation()}
                size="lg"
                type="button"
                variant="secondary"
              >
                {geoLoading ? "Obteniendo ubicación..." : "Usar ubicación actual"}
              </Button>

              {geoMessage ? (
                <div className="rounded-[1.25rem] border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
                  {geoMessage}
                </div>
              ) : null}

              <Textarea
                label={activeAction.requiresComment ? "Comentario" : "Comentario (opcional)"}
                onChange={(event) => updateOperationalField("comentario", event.target.value)}
                placeholder={`Agrega contexto para ${activeAction.label.toLowerCase()}`}
                required={activeAction.requiresComment}
                value={operationalForm.comentario}
              />

              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">
                      Evidencias de esta acción
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      Agrega una o más fotos o archivos relacionados con esta acción operativa.
                    </p>
                  </div>
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                    {actionEvidences.length} nuevas
                  </span>
                </div>

                <div className="mt-4 grid gap-4">
                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-slate-700">Archivo</span>
                    <input
                      accept="image/*,.pdf,.doc,.docx"
                      className="block w-full rounded-[1.25rem] border border-slate-300 px-4 py-3 text-sm"
                      onChange={(event) =>
                        setActionEvidenceDraft((current) => ({
                          ...current,
                          file: event.target.files?.[0] ?? null,
                        }))
                      }
                      type="file"
                    />
                  </label>

                  <label className="block space-y-2">
                    <span className="text-sm font-medium text-slate-700">Tipo de evidencia</span>
                    <select
                      className="w-full rounded-[1.25rem] border border-slate-300 px-4 py-3 text-sm"
                      disabled={loadingTiposEvidencia}
                      onChange={(event) =>
                        setActionEvidenceDraft((current) => ({
                          ...current,
                          idTipoEvidencia: event.target.value,
                        }))
                      }
                      value={actionEvidenceDraft.idTipoEvidencia}
                    >
                      <option value="">Selecciona un tipo</option>
                      {tiposEvidencia.map((tipo) => (
                        <option key={tipo.id_tipo_evidencia} value={tipo.id_tipo_evidencia}>
                          {tipo.nombre}
                        </option>
                      ))}
                    </select>
                  </label>

                  <Textarea
                    label="Comentario de evidencia"
                    onChange={(event) =>
                      setActionEvidenceDraft((current) => ({
                        ...current,
                        comentario: event.target.value,
                      }))
                    }
                    placeholder="Comentario opcional para esta evidencia"
                    value={actionEvidenceDraft.comentario}
                  />

                  <div className="flex flex-wrap items-center gap-3">
                    <Button
                      disabled={uploadingEvidence || loadingTiposEvidencia || !actionEvidenceDraft.file}
                      onClick={() => void handleAddEvidence()}
                      size="sm"
                      type="button"
                      variant="secondary"
                    >
                      {uploadingEvidence ? "Subiendo evidencia..." : "Agregar evidencia"}
                    </Button>
                    {loadingExistingEvidencias ? (
                      <span className="text-sm text-slate-500">Revisando evidencias existentes...</span>
                    ) : (
                      <span className="text-sm text-slate-500">
                        Evidencias ya asociadas al viaje: {existingEvidencias.length}
                      </span>
                    )}
                  </div>

                  {actionEvidences.length > 0 ? (
                    <div className="space-y-3">
                      {actionEvidences.map((item) => {
                        const tipo = tiposEvidencia.find(
                          (tipoItem) => tipoItem.id_tipo_evidencia === item.data.id_tipo_evidencia
                        );
                        return (
                          <div
                            className="flex flex-wrap items-center justify-between gap-3 rounded-[1.25rem] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
                            key={item.tempId}
                          >
                            <div>
                              <p className="font-medium text-slate-900">{item.nombreArchivo}</p>
                              <p className="text-xs text-slate-500">
                                {tipo?.nombre ?? "Tipo seleccionado"}
                                {item.data.comentario ? ` · ${item.data.comentario}` : ""}
                              </p>
                            </div>
                            <Button onClick={() => removeEvidence(item.tempId)} type="button" variant="ghost">
                              Quitar
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}

                  {evidenceError ? (
                    <div className="rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                      {evidenceError}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            {currentError ? (
              <div className="mt-4 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {currentError}
              </div>
            ) : null}

            {!currentError && validationError ? (
              <div className="mt-4 rounded-[1.25rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {validationError}
              </div>
            ) : null}

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <Button
                className="min-h-14 rounded-[1.25rem] text-base font-semibold"
                disabled={loadingAction !== null}
                onClick={closeOperationalSheet}
                size="lg"
                type="button"
                variant="ghost"
              >
                Cancelar
              </Button>
              <Button
                className="min-h-14 rounded-[1.25rem] text-base font-semibold"
                disabled={submitDisabled}
                onClick={() => void handleActionSubmit()}
                size="lg"
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
