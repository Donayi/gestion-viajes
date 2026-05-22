"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useSession } from "@/hooks/use-session";
import { formatDateTime } from "@/lib/formatters";
import { isAdmin } from "@/lib/permissions";
import { ApiError } from "@/services/api-client";
import { updateEventoOperativoRequest } from "@/services/viajes.service";
import type { EvidenciaResponse } from "@/types/evidencia";
import type { EventoOperativoViaje } from "@/types/viaje";

const eventLabels: Record<EventoOperativoViaje["tipo_evento"], string> = {
  INICIO_CARGA: "Inicio de carga",
  INICIO_VIAJE: "Inicio de viaje",
  REINICIO_VIAJE: "Reinicio de viaje",
  RETRASO: "Retraso",
  STANDBY_SOLICITADO: "Solicitud de standby",
  STANDBY: "Standby",
  FINALIZACION_VIAJE: "Finalización"
};

type EventFormState = {
  kilometraje: string;
  nivel_diesel: string;
  ubicacion: string;
  latitud: string;
  longitud: string;
  comentario: string;
};

type PreviewState = {
  evidencia: EvidenciaResponse;
  kind: "image" | "pdf" | "unsupported";
} | null;

function toFormState(evento: EventoOperativoViaje): EventFormState {
  return {
    kilometraje: evento.kilometraje !== null ? String(evento.kilometraje) : "",
    nivel_diesel: evento.nivel_diesel !== null ? String(evento.nivel_diesel) : "",
    ubicacion: evento.ubicacion,
    latitud: evento.latitud !== null ? String(evento.latitud) : "",
    longitud: evento.longitud !== null ? String(evento.longitud) : "",
    comentario: evento.comentario ?? ""
  };
}

function isImageEvidence(evidencia: EvidenciaResponse) {
  const contentType = evidencia.archivo?.content_type?.toLowerCase() ?? "";
  const extension = evidencia.archivo?.extension?.toLowerCase() ?? "";
  const fileName = evidencia.archivo?.nombre_original?.toLowerCase() ?? "";

  return (
    contentType.startsWith("image/") ||
    [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"].some((suffix) =>
      extension.endsWith(suffix) || fileName.endsWith(suffix)
    )
  );
}

function getEvidenceLabel(evidencia: EvidenciaResponse) {
  return (
    evidencia.archivo?.nombre_original ??
    evidencia.archivo?.nombre_guardado ??
    `Evidencia #${evidencia.id_evidencia}`
  );
}

function isPdfEvidence(evidencia: EvidenciaResponse) {
  const contentType = evidencia.archivo?.content_type?.toLowerCase() ?? "";
  const extension = evidencia.archivo?.extension?.toLowerCase() ?? "";
  const fileName = evidencia.archivo?.nombre_original?.toLowerCase() ?? "";

  return (
    contentType.includes("pdf") ||
    extension.endsWith(".pdf") ||
    fileName.endsWith(".pdf")
  );
}

export function ViajeEventosOperativos({
  viajeId,
  eventos,
  onCorrected
}: {
  viajeId: number;
  eventos: EventoOperativoViaje[];
  onCorrected?: () => Promise<void> | void;
}) {
  const { user } = useSession();
  const canCorrect = useMemo(() => isAdmin(user), [user]);
  const [editingEvent, setEditingEvent] = useState<EventoOperativoViaje | null>(null);
  const [form, setForm] = useState<EventFormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewState>(null);

  function openCorrection(evento: EventoOperativoViaje) {
    setEditingEvent(evento);
    setForm(toFormState(evento));
    setError(null);
  }

  function closeCorrection() {
    if (saving) return;
    setEditingEvent(null);
    setForm(null);
    setError(null);
  }

  function openPreview(evidencia: EvidenciaResponse) {
    if (isImageEvidence(evidencia)) {
      setPreview({ evidencia, kind: "image" });
      return;
    }

    if (isPdfEvidence(evidencia)) {
      setPreview({ evidencia, kind: "pdf" });
      return;
    }

    setPreview({ evidencia, kind: "unsupported" });
  }

  function closePreview() {
    setPreview(null);
  }

  async function handleSaveCorrection() {
    if (!editingEvent || !form) return;

    if (!form.ubicacion.trim()) {
      setError("La ubicación es obligatoria.");
      return;
    }

    if ((form.latitud.trim() && !form.longitud.trim()) || (!form.latitud.trim() && form.longitud.trim())) {
      setError("Latitud y longitud deben enviarse juntas.");
      return;
    }

    const payload = {
      kilometraje: form.kilometraje.trim() ? Number(form.kilometraje) : null,
      nivel_diesel: form.nivel_diesel.trim() ? Number(form.nivel_diesel) : null,
      ubicacion: form.ubicacion.trim(),
      latitud: form.latitud.trim() ? Number(form.latitud) : null,
      longitud: form.longitud.trim() ? Number(form.longitud) : null,
      comentario: form.comentario.trim() || null
    };

    setSaving(true);
    setError(null);

    try {
      await updateEventoOperativoRequest(viajeId, editingEvent.id_evento, payload);
      await onCorrected?.();
      closeCorrection();
    } catch (currentError) {
      setError(
        currentError instanceof ApiError
          ? currentError.message
          : "No fue posible corregir el evento operativo"
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Card className="p-5 md:p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
              KPIs de campo
            </p>
            <h2 className="mt-2 text-lg font-semibold text-slate-950">Eventos operativos</h2>
          </div>
          <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
            {eventos.length}
          </span>
        </div>

        {eventos.length === 0 ? (
          <div className="mt-5 rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
            Aún no hay capturas operativas para este viaje.
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {eventos.map((evento) => (
              <div
                key={evento.id_evento}
                className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">
                      {eventLabels[evento.tipo_evento]}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">{formatDateTime(evento.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {canCorrect ? (
                      <Button onClick={() => openCorrection(evento)} type="button" variant="ghost">
                        Corregir
                      </Button>
                    ) : null}
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                      #{evento.id_evento}
                    </span>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <Metric
                    label="Kilometraje"
                    value={evento.kilometraje !== null ? `${evento.kilometraje} km` : "No aplica"}
                  />
                  <Metric
                    label="Diésel"
                    value={evento.nivel_diesel !== null ? `${evento.nivel_diesel}%` : "No aplica"}
                  />
                  <Metric label="Ubicación" value={evento.ubicacion} />
                  <Metric
                    label="Coordenadas"
                    value={
                      evento.latitud !== null && evento.longitud !== null
                        ? `${evento.latitud}, ${evento.longitud}`
                        : "Sin geolocalización"
                    }
                  />
                </div>

                {evento.comentario ? (
                  <div className="mt-4 rounded-[1.25rem] bg-white px-3 py-3 text-sm text-slate-700">
                    {evento.comentario}
                  </div>
                ) : null}

                <div className="mt-4 rounded-[1.25rem] bg-white px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Evidencias
                    </p>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                      {evento.evidencias.length}
                    </span>
                  </div>

                  {evento.evidencias.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">Sin evidencias registradas</p>
                  ) : (
                    <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {evento.evidencias.map((evidencia) => {
                        const url = evidencia.archivo?.url_publica;
                        const label = getEvidenceLabel(evidencia);
                        const image = isImageEvidence(evidencia);
                        const pdf = isPdfEvidence(evidencia);
                        const mime = evidencia.archivo?.content_type;

                        return (
                          <div
                            className="group overflow-hidden rounded-[1.25rem] border border-slate-200 bg-slate-50 transition hover:border-brand-300 hover:bg-brand-50"
                            key={evidencia.id_evidencia}
                          >
                            {image && url ? (
                              <img
                                alt={label}
                                className="h-32 w-full object-cover transition group-hover:scale-[1.02]"
                                src={url}
                              />
                            ) : (
                              <div className="flex h-32 items-center justify-center bg-slate-100 px-4 text-center text-sm font-medium text-slate-500">
                                Archivo sin vista previa
                              </div>
                            )}

                            <div className="space-y-2 px-3 py-3">
                              <p className="line-clamp-2 text-sm font-medium text-slate-900">{label}</p>
                              {mime ? (
                                <p className="text-[11px] text-slate-500">{mime}</p>
                              ) : null}
                              {evidencia.comentario ? (
                                <p className="line-clamp-2 text-xs text-slate-600">{evidencia.comentario}</p>
                              ) : null}

                              <div className="flex flex-wrap gap-2 pt-1">
                                {canCorrect ? (
                                  <>
                                    {url ? (
                                      <Button
                                        className="min-h-9 rounded-lg px-3 py-2 text-xs"
                                        onClick={() => openPreview(evidencia)}
                                        title="Vista previa del archivo"
                                        type="button"
                                        variant="secondary"
                                      >
                                        Ver
                                      </Button>
                                    ) : (
                                      <span className="inline-flex min-h-9 items-center rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-500">
                                        Sin URL disponible
                                      </span>
                                    )}
                                    {url ? (
                                      <a
                                        download={label}
                                        href={url}
                                        rel="noopener noreferrer"
                                        target="_blank"
                                        title="Descargar archivo"
                                      >
                                        <Button className="min-h-9 rounded-lg px-3 py-2 text-xs" type="button" variant="ghost">
                                          Descargar
                                        </Button>
                                      </a>
                                    ) : (
                                      <span className="inline-flex min-h-9 items-center rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-500">
                                        Sin URL disponible
                                      </span>
                                    )}
                                  </>
                                ) : url ? (
                                  <a
                                    className="text-[11px] font-medium text-brand-700"
                                    href={url}
                                    rel="noopener noreferrer"
                                    target="_blank"
                                  >
                                    {image || pdf ? "Abrir archivo" : "Descargar archivo"}
                                  </a>
                                ) : (
                                  <p className="text-[11px] font-medium text-slate-500">
                                    Archivo sin URL pública
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {editingEvent && form ? (
        <div className="fixed inset-0 z-50 flex items-end bg-slate-950/45 backdrop-blur-sm">
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-[2rem] bg-white px-5 pb-8 pt-5 shadow-2xl md:mx-auto md:mb-6 md:max-w-xl md:rounded-[2rem]">
            <div className="mx-auto h-1.5 w-14 rounded-full bg-slate-200 md:hidden" />

            <div className="mt-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
                  Corrección administrativa
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">
                  {eventLabels[editingEvent.tipo_evento]}
                </h3>
              </div>
              <Button onClick={closeCorrection} type="button" variant="ghost">
                Cerrar
              </Button>
            </div>

            <div className="mt-6 grid gap-4">
              <Input
                inputMode="decimal"
                label="Kilometraje"
                onChange={(event) => setForm((current) => current ? { ...current, kilometraje: event.target.value } : current)}
                type="number"
                value={form.kilometraje}
              />
              <Input
                inputMode="decimal"
                label="Nivel de diésel (%)"
                onChange={(event) => setForm((current) => current ? { ...current, nivel_diesel: event.target.value } : current)}
                type="number"
                value={form.nivel_diesel}
              />
              <Input
                label="Ubicación"
                onChange={(event) => setForm((current) => current ? { ...current, ubicacion: event.target.value } : current)}
                value={form.ubicacion}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  inputMode="decimal"
                  label="Latitud"
                  onChange={(event) => setForm((current) => current ? { ...current, latitud: event.target.value } : current)}
                  type="number"
                  value={form.latitud}
                />
                <Input
                  inputMode="decimal"
                  label="Longitud"
                  onChange={(event) => setForm((current) => current ? { ...current, longitud: event.target.value } : current)}
                  type="number"
                  value={form.longitud}
                />
              </div>
              <Textarea
                label="Comentario"
                onChange={(event) => setForm((current) => current ? { ...current, comentario: event.target.value } : current)}
                value={form.comentario}
              />
            </div>

            {error ? (
              <div className="mt-4 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            ) : null}

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <Button
                className="min-h-14 rounded-[1.25rem] text-base font-semibold"
                disabled={saving}
                onClick={closeCorrection}
                type="button"
                variant="ghost"
              >
                Cancelar
              </Button>
              <Button
                className="min-h-14 rounded-[1.25rem] text-base font-semibold"
                disabled={saving}
                onClick={() => void handleSaveCorrection()}
                type="button"
              >
                {saving ? "Guardando..." : "Guardar corrección"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {preview ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-[2rem] bg-white shadow-2xl">
            <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
                  Vista previa
                </p>
                <h3 className="mt-1 text-lg font-semibold text-slate-950">
                  {getEvidenceLabel(preview.evidencia)}
                </h3>
              </div>
              <Button onClick={closePreview} type="button" variant="ghost">
                Cerrar
              </Button>
            </div>

            <div className="max-h-[calc(90vh-96px)] overflow-auto p-5">
              {preview.kind === "image" && preview.evidencia.archivo?.url_publica ? (
                <img
                  alt={getEvidenceLabel(preview.evidencia)}
                  className="mx-auto max-h-[70vh] w-auto rounded-[1.5rem] object-contain"
                  src={preview.evidencia.archivo.url_publica}
                />
              ) : null}

              {preview.kind === "pdf" && preview.evidencia.archivo?.url_publica ? (
                <iframe
                  className="h-[70vh] w-full rounded-[1.5rem] border border-slate-200"
                  src={preview.evidencia.archivo.url_publica}
                  title={getEvidenceLabel(preview.evidencia)}
                />
              ) : null}

              {preview.kind === "unsupported" ? (
                <div className="rounded-[1.5rem] border border-amber-200 bg-amber-50 px-4 py-5 text-sm text-amber-800">
                  Vista previa no disponible. Puedes descargar el archivo.
                </div>
              ) : null}

              <div className="mt-4 flex flex-wrap gap-3">
                {preview.evidencia.archivo?.url_publica ? (
                  <>
                    <a
                      href={preview.evidencia.archivo.url_publica}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      <Button type="button" variant="secondary">
                        Abrir en nueva pestaña
                      </Button>
                    </a>
                    <a
                      download={getEvidenceLabel(preview.evidencia)}
                      href={preview.evidencia.archivo.url_publica}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      <Button type="button" variant="ghost">
                        Descargar
                      </Button>
                    </a>
                  </>
                ) : (
                  <p className="text-sm text-slate-500">Esta evidencia no tiene URL pública disponible.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] bg-white px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-900">{value}</p>
    </div>
  );
}
