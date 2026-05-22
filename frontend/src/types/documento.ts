import type { EvidenciaResponse } from "@/types/evidencia";

export type DocumentoEntidadTipo = "OPERADOR" | "TRAILER" | "CAJA";

export type TipoDocumento = {
  id_tipo_documento: number;
  nombre: string;
  descripcion: string | null;
  aplica_a: string;
  requiere_vigencia: boolean;
};

export type DocumentoArchivo = EvidenciaResponse["archivo"];

export type DocumentoRecord = {
  id_documento: number;
  entidad_tipo: DocumentoEntidadTipo;
  entidad_id: number;
  id_tipo_documento: number;
  id_archivo: number;
  comentario: string | null;
  fecha_vencimiento: string | null;
  estatus: string;
  activo: boolean;
  subido_por: number | null;
  created_at: string;
  updated_at: string;
  tipo_documento: TipoDocumento | null;
  archivo: DocumentoArchivo | null;
};

export type CreateDocumentoPayload = {
  entidad_tipo: DocumentoEntidadTipo;
  entidad_id: number;
  id_tipo_documento: number;
  id_archivo: number;
  comentario?: string | null;
  fecha_vencimiento?: string | null;
  activo?: boolean;
};

export type UpdateDocumentoPayload = {
  id_tipo_documento?: number | null;
  id_archivo?: number | null;
  comentario?: string | null;
  fecha_vencimiento?: string | null;
  activo?: boolean | null;
};
