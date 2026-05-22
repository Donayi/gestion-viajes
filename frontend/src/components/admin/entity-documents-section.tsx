"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/services/api-client";
import {
  createDocumentoRequest,
  deleteDocumentoRequest,
  getDocumentosRequest,
  getTiposDocumentoRequest,
  updateDocumentoRequest,
} from "@/services/documentos.service";
import { getPresignedUrlRequest, uploadFileToR2 } from "@/services/evidencias.service";
import type {
  CreateDocumentoPayload,
  DocumentoEntidadTipo,
  DocumentoRecord,
  TipoDocumento,
  UpdateDocumentoPayload,
} from "@/types/documento";

type DocumentoFormState = {
  id_tipo_documento: string;
  comentario: string;
  fecha_vencimiento: string;
  activo: boolean;
};

const initialForm: DocumentoFormState = {
  id_tipo_documento: "",
  comentario: "",
  fecha_vencimiento: "",
  activo: true,
};

function toFormState(documento: DocumentoRecord | null): DocumentoFormState {
  if (!documento) {
    return initialForm;
  }

  return {
    id_tipo_documento: String(documento.id_tipo_documento),
    comentario: documento.comentario ?? "",
    fecha_vencimiento: documento.fecha_vencimiento ?? "",
    activo: documento.activo,
  };
}

export function EntityDocumentsSection({
  entityType,
  entityId,
}: {
  entityType: DocumentoEntidadTipo;
  entityId: number | null;
}) {
  const [documentos, setDocumentos] = useState<DocumentoRecord[]>([]);
  const [tipos, setTipos] = useState<TipoDocumento[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [form, setForm] = useState<DocumentoFormState>(initialForm);
  const [editingDocumento, setEditingDocumento] = useState<DocumentoRecord | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const title = useMemo(() => {
    return {
      OPERADOR: "Documentos del operador",
      TRAILER: "Documentos del tráiler",
      CAJA: "Documentos de la caja",
    }[entityType];
  }, [entityType]);

  const load = useCallback(async () => {
    if (!entityId) {
      return;
    }

    setLoading(true);
    setLoadingError(null);
    try {
      const [tiposData, documentosData] = await Promise.all([
        getTiposDocumentoRequest(entityType),
        getDocumentosRequest(entityType, entityId),
      ]);
      setTipos(tiposData);
      setDocumentos(documentosData);
      setForm((current) => ({
        ...current,
        id_tipo_documento: current.id_tipo_documento || String(tiposData[0]?.id_tipo_documento ?? ""),
      }));
    } catch (currentError) {
      setLoadingError(
        currentError instanceof ApiError ? currentError.message : "No fue posible cargar documentos"
      );
    } finally {
      setLoading(false);
    }
  }, [entityId, entityType]);

  useEffect(() => {
    void load();
  }, [load]);

  function resetForm() {
    setForm({
      ...initialForm,
      id_tipo_documento: String(tipos[0]?.id_tipo_documento ?? ""),
    });
    setEditingDocumento(null);
    setSelectedFile(null);
    setFormError(null);
  }

  async function uploadSelectedFile(): Promise<number | null> {
    if (!selectedFile) {
      return editingDocumento?.id_archivo ?? null;
    }

    const presign = await getPresignedUrlRequest({
      filename: selectedFile.name,
      content_type: selectedFile.type || "application/octet-stream",
      size_bytes: selectedFile.size,
    });

    await uploadFileToR2(presign.upload_url, selectedFile);
    return presign.id_archivo;
  }

  async function handleSubmit() {
    if (!entityId) {
      setFormError("Guarda primero el registro para poder adjuntar documentos.");
      return;
    }

    if (!form.id_tipo_documento) {
      setFormError("Selecciona un tipo de documento.");
      return;
    }

    if (!editingDocumento && !selectedFile) {
      setFormError("Selecciona un archivo para cargar el documento.");
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const idArchivo = await uploadSelectedFile();
      if (!idArchivo) {
        throw new Error("No fue posible resolver el archivo del documento");
      }

      if (editingDocumento) {
        const payload: UpdateDocumentoPayload = {
          id_tipo_documento: Number(form.id_tipo_documento),
          comentario: form.comentario.trim() || null,
          fecha_vencimiento: form.fecha_vencimiento || null,
          activo: form.activo,
          ...(selectedFile ? { id_archivo: idArchivo } : {}),
        };
        await updateDocumentoRequest(editingDocumento.id_documento, payload);
      } else {
        const payload: CreateDocumentoPayload = {
          entidad_tipo: entityType,
          entidad_id: entityId,
          id_tipo_documento: Number(form.id_tipo_documento),
          id_archivo: idArchivo,
          comentario: form.comentario.trim() || null,
          fecha_vencimiento: form.fecha_vencimiento || null,
          activo: form.activo,
        };
        await createDocumentoRequest(payload);
      }

      resetForm();
      await load();
    } catch (currentError) {
      setFormError(
        currentError instanceof ApiError
          ? currentError.message
          : currentError instanceof Error
            ? currentError.message
            : "No fue posible guardar el documento"
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeactivate(documento: DocumentoRecord) {
    const confirmed = window.confirm(
      documento.activo
        ? "¿Deseas desactivar este documento?"
        : "¿Deseas reactivar este documento?"
    );
    if (!confirmed) return;

    try {
      if (documento.activo) {
        await deleteDocumentoRequest(documento.id_documento);
      } else {
        await updateDocumentoRequest(documento.id_documento, { activo: true });
      }
      await load();
    } catch (currentError) {
      setLoadingError(
        currentError instanceof ApiError ? currentError.message : "No fue posible actualizar el documento"
      );
    }
  }

  return (
    <div className="mt-6 space-y-4 rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">Documentos</p>
          <p className="mt-1 text-sm text-slate-600">{title}</p>
        </div>
        {entityId ? (
          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
            {documentos.length} cargados
          </span>
        ) : null}
      </div>

      {!entityId ? (
        <div className="rounded-[1.25rem] border border-dashed border-slate-300 bg-white px-4 py-4 text-sm text-slate-600">
          Guarda primero el registro para poder adjuntar documentos.
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block space-y-2 md:col-span-2">
              <span className="text-sm font-medium text-slate-700">Archivo</span>
              <input
                className="block w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                type="file"
              />
              {selectedFile ? (
                <p className="text-xs text-slate-500">Archivo seleccionado: {selectedFile.name}</p>
              ) : editingDocumento?.archivo?.nombre_original ? (
                <p className="text-xs text-slate-500">
                  Archivo actual: {editingDocumento.archivo.nombre_original}
                </p>
              ) : null}
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700">Tipo de documento</span>
              <select
                className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
                onChange={(event) => setForm((current) => ({ ...current, id_tipo_documento: event.target.value }))}
                value={form.id_tipo_documento}
              >
                <option value="">Selecciona un tipo</option>
                {tipos.map((tipo) => (
                  <option key={tipo.id_tipo_documento} value={tipo.id_tipo_documento}>
                    {tipo.nombre}
                  </option>
                ))}
              </select>
            </label>

            <Input
              label="Fecha de vencimiento"
              onChange={(event) => setForm((current) => ({ ...current, fecha_vencimiento: event.target.value }))}
              type="date"
              value={form.fecha_vencimiento}
            />

            <Textarea
              label="Comentario"
              onChange={(event) => setForm((current) => ({ ...current, comentario: event.target.value }))}
              value={form.comentario}
            />

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 md:col-span-2">
              <input
                checked={form.activo}
                onChange={(event) => setForm((current) => ({ ...current, activo: event.target.checked }))}
                type="checkbox"
              />
              Documento activo
            </label>
          </div>

          {formError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {formError}
            </div>
          ) : null}

          <div className="flex gap-3">
            <Button disabled={submitting || loading} onClick={() => void handleSubmit()} type="button">
              {submitting ? "Guardando..." : editingDocumento ? "Guardar documento" : "Agregar documento"}
            </Button>
            {editingDocumento ? (
              <Button onClick={resetForm} type="button" variant="secondary">
                Cancelar edición
              </Button>
            ) : null}
          </div>

          {loadingError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {loadingError}
            </div>
          ) : null}

          {loading ? (
            <div className="rounded-[1.25rem] bg-white px-4 py-4 text-sm text-slate-500">
              Cargando documentos...
            </div>
          ) : documentos.length === 0 ? (
            <div className="rounded-[1.25rem] bg-white px-4 py-4 text-sm text-slate-500">
              Aún no hay documentos cargados para esta entidad.
            </div>
          ) : (
            <div className="space-y-3">
              {documentos.map((documento) => (
                <div
                  className="rounded-[1.25rem] border border-slate-200 bg-white px-4 py-4"
                  key={documento.id_documento}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">
                        {documento.tipo_documento?.nombre ?? `Documento #${documento.id_documento}`}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {documento.archivo?.nombre_original ?? "Archivo sin nombre"}
                      </p>
                      {documento.comentario ? (
                        <p className="mt-2 text-sm text-slate-600">{documento.comentario}</p>
                      ) : null}
                      {documento.fecha_vencimiento ? (
                        <p className="mt-1 text-xs text-slate-500">
                          Vence: {documento.fecha_vencimiento}
                        </p>
                      ) : null}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {documento.archivo?.url_publica ? (
                        <>
                          <a href={documento.archivo.url_publica} rel="noopener noreferrer" target="_blank">
                            <Button type="button" variant="secondary">Ver</Button>
                          </a>
                          <a
                            download={documento.archivo.nombre_original ?? `documento-${documento.id_documento}`}
                            href={documento.archivo.url_publica}
                            rel="noopener noreferrer"
                            target="_blank"
                          >
                            <Button type="button" variant="ghost">Descargar</Button>
                          </a>
                        </>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slate-500">
                          Sin URL disponible
                        </span>
                      )}
                      <Button onClick={() => {
                        setEditingDocumento(documento);
                        setForm(toFormState(documento));
                        setSelectedFile(null);
                        setFormError(null);
                      }} type="button" variant="secondary">
                        Editar
                      </Button>
                      <Button
                        onClick={() => void handleDeactivate(documento)}
                        type="button"
                        variant={documento.activo ? "danger" : "secondary"}
                      >
                        {documento.activo ? "Desactivar" : "Reactivar"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
