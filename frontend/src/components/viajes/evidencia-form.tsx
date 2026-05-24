"use client";

import { useEffect, useState } from "react";

import { useSession } from "@/hooks/use-session";
import { isAdmin, isOperador } from "@/lib/permissions";
import {
  createEvidenciaRequest,
  getPresignedUrlRequest,
  getTiposEvidenciaRequest,
  uploadFileToR2
} from "@/services/evidencias.service";
import type { TipoEvidencia } from "@/types/evidencia";
import { Button } from "@/components/ui/button";
import { EvidenceFilePicker } from "@/components/ui/evidence-file-picker";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/services/api-client";
import {
  prepareEvidenceFile,
  revokePreparedEvidenceFile,
  type PreparedEvidenceFile,
} from "@/lib/evidence-files";

export function EvidenciaForm({
  viajeId,
  onSuccess
}: {
  viajeId: number;
  onSuccess: () => Promise<void>;
}) {
  const { user } = useSession();
  const adminUser = isAdmin(user);
  const operadorUser = isOperador(user);
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<PreparedEvidenceFile | null>(null);
  const [comentario, setComentario] = useState("");
  const [tipos, setTipos] = useState<TipoEvidencia[]>([]);
  const [selectedTipo, setSelectedTipo] = useState<string>("");
  const [loadingTipos, setLoadingTipos] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      revokePreparedEvidenceFile(file);
    };
  }, [file]);

  useEffect(() => {
    if (!open) return;

    let cancelled = false;

    async function loadTipos() {
      setLoadingTipos(true);
      setError(null);

      try {
        const data = await getTiposEvidenciaRequest();
        if (cancelled) return;
        setTipos(data);
        setSelectedTipo((current) => current || String(data[0]?.id_tipo_evidencia ?? ""));
      } catch (error) {
        if (cancelled) return;
        const message =
          error instanceof ApiError ? error.message : "No fue posible cargar tipos de evidencia";
        setError(message);
      } finally {
        if (!cancelled) {
          setLoadingTipos(false);
        }
      }
    }

    void loadTipos();

    return () => {
      cancelled = true;
    };
  }, [open]);

  async function handleSubmit() {
    if (!file) {
      setError("Selecciona un archivo antes de subir evidencia");
      return;
    }

    if (!selectedTipo) {
      setError("Selecciona un tipo de evidencia");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const presign = await getPresignedUrlRequest({
        filename: file.file.name,
        content_type: file.file.type || "application/octet-stream",
        size_bytes: file.file.size
      });

      await uploadFileToR2(presign.upload_url, file.file);

      await createEvidenciaRequest(viajeId, {
        id_tipo_evidencia: Number(selectedTipo),
        id_archivo: presign.id_archivo,
        id_operador: user?.id_operador ?? null,
        comentario: comentario || null
      });

      setSuccess("Evidencia subida correctamente");
      setComentario("");
      revokePreparedEvidenceFile(file);
      setFile(null);
      await onSuccess();
      setTimeout(() => {
        setOpen(false);
        setSuccess(null);
      }, 900);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : error instanceof Error ? error.message : "No fue posible subir la evidencia";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileChange(nextFile: File | null) {
    setError(null);

    if (!nextFile) {
      revokePreparedEvidenceFile(file);
      setFile(null);
      return;
    }

    try {
      const preparedFile = await prepareEvidenceFile(nextFile, { allowPdf: adminUser });
      revokePreparedEvidenceFile(file);
      setFile(preparedFile);
    } catch (currentError) {
      setError(
        currentError instanceof Error
          ? currentError.message
          : "No fue posible preparar la imagen seleccionada."
      );
    }
  }

  if (!open) {
    return (
      <Button
        className="min-h-14 w-full rounded-[1.25rem] text-base font-semibold"
        onClick={() => setOpen(true)}
        type="button"
        variant="primary"
      >
        Subir evidencia
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-40 flex items-end bg-slate-950/60 backdrop-blur-sm">
      <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-[2rem] bg-white p-5 shadow-soft">
        <div className="mx-auto mb-4 h-1.5 w-16 rounded-full bg-slate-200" />

        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
              Evidencia
            </p>
            <h3 className="mt-2 text-2xl font-semibold text-slate-950">Subir archivo</h3>
          </div>
          <Button onClick={() => setOpen(false)} type="button" variant="ghost">
            Cerrar
          </Button>
        </div>

        <div className="mt-5 space-y-4">
          <EvidenceFilePicker
            disabled={loading}
            helperText={
              adminUser
                ? "Puedes seleccionar imágenes guardadas o PDFs. No se forzará la cámara."
                : "En celular se intentará abrir la cámara trasera. En escritorio puedes seleccionar una imagen."
            }
            label={adminUser ? "Archivo de evidencia" : "Foto de evidencia"}
            mode={adminUser ? "file" : operadorUser ? "camera" : "mixed"}
            onFileChange={(nextFile) => void handleFileChange(nextFile)}
            selectedFile={file}
          />

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Tipo de evidencia</span>
            <select
              className="w-full rounded-[1.25rem] border border-slate-300 px-4 py-3 text-sm"
              disabled={loadingTipos}
              onChange={(event) => setSelectedTipo(event.target.value)}
              value={selectedTipo}
            >
              <option value="">Selecciona un tipo</option>
              {tipos.map((tipo) => (
                <option key={tipo.id_tipo_evidencia} value={tipo.id_tipo_evidencia}>
                  {tipo.nombre}
                </option>
              ))}
            </select>
          </label>

          <Textarea
            label="Comentario"
            onChange={(event) => setComentario(event.target.value)}
            placeholder="Comentario opcional para la evidencia"
            value={comentario}
          />

          {error ? (
            <div className="rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          {success ? (
            <div className="rounded-[1.25rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {success}
            </div>
          ) : null}

          <Button
            className="min-h-14 w-full rounded-[1.25rem] text-base font-semibold"
            disabled={loading || loadingTipos}
            onClick={() => void handleSubmit()}
            type="button"
          >
            {loading ? "Subiendo evidencia..." : "Subir evidencia"}
          </Button>
        </div>
      </div>
    </div>
  );
}
