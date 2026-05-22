export type MantenimientoEntidadTipo = "TRAILER" | "CAJA";
export type MantenimientoTipo = "PREVENTIVO" | "CORRECTIVO" | "REPARACION";
export type MantenimientoEstatus = "ABIERTO" | "EN_PROCESO" | "CERRADO" | "CANCELADO";
export type MantenimientoArchivoTipo =
  | "FOTO_ANTES"
  | "FOTO_DESPUES"
  | "FACTURA"
  | "DIAGNOSTICO"
  | "OTRO";

export type MantenimientoTrailerDisponible = {
  id_trailer: number;
  numero_economico: string;
  placas: string;
};

export type MantenimientoCajaDisponible = {
  id_caja: number;
  numero_economico: string | null;
  placas: string;
};

export type MantenimientoRecursosDisponibles = {
  trailers: MantenimientoTrailerDisponible[];
  cajas: MantenimientoCajaDisponible[];
};

export type MantenimientoEntidadResumen = {
  id: number;
  etiqueta: string;
  subtitulo: string | null;
};

export type MantenimientoChecklistItem = {
  id_item: number;
  id_mantenimiento: number;
  nombre: string;
  descripcion: string | null;
  completado: boolean;
  observaciones: string | null;
  created_at: string;
  updated_at: string;
  evidencias: MantenimientoChecklistEvidenciaRecord[];
};

export type MantenimientoChecklistEvidenciaRecord = {
  id_checklist_evidencia: number;
  id_item: number;
  id_archivo: number;
  comentario: string | null;
  activo: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  archivo: {
    id_archivo: number;
    file_key: string | null;
    nombre_original: string | null;
    nombre_guardado: string | null;
    extension: string | null;
    content_type: string | null;
    url_publica: string | null;
  } | null;
};

export type MantenimientoArchivoRecord = {
  id_mantenimiento_archivo: number;
  id_mantenimiento: number;
  id_archivo: number;
  tipo_archivo: MantenimientoArchivoTipo;
  comentario: string | null;
  activo: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  archivo: {
    id_archivo: number;
    file_key: string | null;
    nombre_original: string | null;
    nombre_guardado: string | null;
    extension: string | null;
    content_type: string | null;
    url_publica: string | null;
  } | null;
};

export type MantenimientoRecord = {
  id_mantenimiento: number;
  entidad_tipo: MantenimientoEntidadTipo;
  entidad_id: number;
  id_trailer: number | null;
  id_caja: number | null;
  tipo_mantenimiento: MantenimientoTipo;
  estatus: MantenimientoEstatus;
  fecha_inicio: string;
  fecha_mantenimiento: string | null;
  fecha_proximo_mantenimiento: string | null;
  fecha_fin: string | null;
  kilometraje: number | null;
  descripcion: string;
  observaciones: string | null;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
  entidad: MantenimientoEntidadResumen;
  checklist_items: MantenimientoChecklistItem[];
  archivos: MantenimientoArchivoRecord[];
};

export type CreateMantenimientoPayload = {
  entidad_tipo: MantenimientoEntidadTipo;
  entidad_id: number;
  tipo_mantenimiento: MantenimientoTipo;
  fecha_mantenimiento?: string | null;
  fecha_proximo_mantenimiento?: string | null;
  kilometraje?: number | null;
  descripcion: string;
  observaciones?: string | null;
};

export type UpdateMantenimientoPayload = {
  tipo_mantenimiento?: MantenimientoTipo;
  estatus?: MantenimientoEstatus;
  fecha_mantenimiento?: string | null;
  fecha_proximo_mantenimiento?: string | null;
  kilometraje?: number | null;
  descripcion?: string;
  observaciones?: string | null;
};

export type UpdateMantenimientoChecklistItemPayload = {
  completado?: boolean;
  observaciones?: string | null;
};

export type MantenimientoCambioEstadoPayload = {
  observaciones?: string | null;
};

export type CreateMantenimientoArchivoPayload = {
  id_archivo: number;
  tipo_archivo: MantenimientoArchivoTipo;
  comentario?: string | null;
};

export type UpdateMantenimientoArchivoPayload = {
  tipo_archivo?: MantenimientoArchivoTipo;
  comentario?: string | null;
  activo?: boolean;
};

export type CreateMantenimientoChecklistEvidenciaPayload = {
  id_archivo: number;
  comentario?: string | null;
};

export type UpdateMantenimientoChecklistEvidenciaPayload = {
  comentario?: string | null;
  activo?: boolean;
};
