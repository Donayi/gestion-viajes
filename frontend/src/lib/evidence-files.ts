"use client";

export const ALLOWED_EVIDENCE_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
export const ALLOWED_EVIDENCE_FILE_TYPES = ["image/*", "application/pdf"] as const;

const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const MAX_DIMENSION = 1600;

export type PreparedEvidenceFile = {
  file: File;
  previewUrl: string | null;
};

type PrepareEvidenceFileOptions = {
  allowPdf?: boolean;
};

function formatExtension(contentType: string) {
  if (contentType === "image/png") return "png";
  if (contentType === "image/webp") return "webp";
  return "jpg";
}

function buildFilename(originalName: string, contentType: string) {
  const baseName = originalName.replace(/\.[^.]+$/, "") || "evidencia";
  return `${baseName}.${formatExtension(contentType)}`;
}

function loadImage(file: File) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    const url = URL.createObjectURL(file);
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("No fue posible procesar la imagen seleccionada."));
    };
    image.src = url;
  });
}

function canvasToBlob(canvas: HTMLCanvasElement, contentType: string, quality: number) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("No fue posible comprimir la imagen seleccionada."));
          return;
        }
        resolve(blob);
      },
      contentType,
      quality
    );
  });
}

export function validateEvidenceFile(file: File, options?: PrepareEvidenceFileOptions) {
  if (options?.allowPdf && file.type === "application/pdf") {
    return;
  }

  if (!ALLOWED_EVIDENCE_TYPES.includes(file.type as (typeof ALLOWED_EVIDENCE_TYPES)[number])) {
    throw new Error("Solo se permiten imágenes JPEG, PNG o WEBP.");
  }
}

export async function prepareEvidenceFile(
  file: File,
  options?: PrepareEvidenceFileOptions
): Promise<PreparedEvidenceFile> {
  validateEvidenceFile(file, options);

  if (options?.allowPdf && file.type === "application/pdf") {
    return {
      file,
      previewUrl: null,
    };
  }

  let processedFile = file;
  const shouldCompress = file.size > MAX_IMAGE_BYTES;

  if (shouldCompress) {
    const image = await loadImage(file);
    const scale = Math.min(1, MAX_DIMENSION / Math.max(image.width, image.height));
    const targetWidth = Math.max(1, Math.round(image.width * scale));
    const targetHeight = Math.max(1, Math.round(image.height * scale));

    const canvas = document.createElement("canvas");
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const context = canvas.getContext("2d");

    if (!context) {
      throw new Error("No fue posible preparar la imagen seleccionada.");
    }

    context.drawImage(image, 0, 0, targetWidth, targetHeight);

    const outputType = file.type === "image/webp" ? "image/webp" : "image/jpeg";
    const blob = await canvasToBlob(canvas, outputType, 0.82);

    processedFile = new File([blob], buildFilename(file.name, outputType), {
      type: outputType,
      lastModified: Date.now(),
    });
  }

  return {
    file: processedFile,
    previewUrl: URL.createObjectURL(processedFile),
  };
}

export function revokePreparedEvidenceFile(preparedFile: PreparedEvidenceFile | null | undefined) {
  if (preparedFile?.previewUrl) {
    URL.revokeObjectURL(preparedFile.previewUrl);
  }
}

export function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}
