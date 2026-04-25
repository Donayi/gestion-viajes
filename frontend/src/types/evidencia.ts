export type TipoEvidencia = {
  id_tipo_evidencia: number;
  nombre: string;
  descripcion: string | null;
};

export type PresignUploadRequest = {
  filename: string;
  content_type: string;
  size_bytes?: number | null;
};

export type PresignUploadResponse = {
  upload_url: string;
  file_key: string;
  id_archivo: number;
};

export type CreateEvidenciaPayload = {
  id_tipo_evidencia: number;
  id_archivo: number;
  id_operador?: number | null;
  comentario?: string | null;
  latitud?: number | null;
  longitud?: number | null;
};

export type EvidenciaResponse = {
  id_evidencia: number;
  id_viaje: number;
  id_tipo_evidencia: number;
  id_operador: number | null;
  id_archivo: number;
  comentario: string | null;
  fecha_captura: string;
  latitud: number | null;
  longitud: number | null;
  created_at: string;
};
