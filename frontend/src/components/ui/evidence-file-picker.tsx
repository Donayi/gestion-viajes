"use client";

import { Button } from "@/components/ui/button";
import { formatFileSize, type PreparedEvidenceFile } from "@/lib/evidence-files";

type EvidencePickerMode = "camera" | "file" | "mixed";

type EvidenceFilePickerProps = {
  selectedFile: PreparedEvidenceFile | null;
  onFileChange: (file: File | null) => void;
  disabled?: boolean;
  helperText?: string;
  error?: string | null;
  label?: string;
  mode?: EvidencePickerMode;
};

export function EvidenceFilePicker({
  selectedFile,
  onFileChange,
  disabled = false,
  helperText,
  error,
  label = "Foto de evidencia",
  mode = "camera",
}: EvidenceFilePickerProps) {
  const accept = mode === "camera" ? "image/*" : "image/*,application/pdf";
  const capture = mode === "camera" ? "environment" : undefined;
  const isImagePreview = Boolean(selectedFile?.previewUrl);

  return (
    <div className="space-y-3">
      <label className="block space-y-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <input
          accept={accept}
          capture={capture}
          className="block w-full rounded-[1.25rem] border border-slate-300 px-4 py-3 text-sm"
          disabled={disabled}
          key={selectedFile?.previewUrl ?? "empty"}
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          type="file"
        />
      </label>

      {helperText ? <p className="text-xs text-slate-500">{helperText}</p> : null}

      {selectedFile ? (
        <div className="rounded-[1.25rem] border border-slate-200 bg-white p-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
            {isImagePreview ? (
              <img
                alt="Vista previa de evidencia"
                className="h-28 w-full rounded-xl object-cover sm:w-28"
                src={selectedFile.previewUrl ?? undefined}
              />
            ) : (
              <div className="flex h-28 w-full items-center justify-center rounded-xl bg-slate-100 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 sm:w-28">
                PDF
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-900">{selectedFile.file.name}</p>
              <p className="mt-1 text-xs text-slate-500">{formatFileSize(selectedFile.file.size)}</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  Lista para subir
                </span>
                <Button onClick={() => onFileChange(null)} size="sm" type="button" variant="ghost">
                  Eliminar
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
    </div>
  );
}
