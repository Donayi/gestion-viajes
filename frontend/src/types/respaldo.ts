export type OrigenRespaldo = "MANUAL" | "AUTOMATICO" | "PRE_RESTAURACION" | "IMPORTADO";
export type EstadoRespaldo =
  | "PENDIENTE"
  | "GENERANDO"
  | "VALIDANDO"
  | "DISPONIBLE"
  | "FALLIDO"
  | "CORRUPTO"
  | "ELIMINADO";

export type RespaldoAdministrativo = {
  id_respaldo: string;
  nombre_archivo: string;
  origen: OrigenRespaldo;
  estado: EstadoRespaldo;
  size_bytes: number | null;
  sha256: string | null;
  table_count: number | null;
  row_count: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_mensaje: string | null;
};

export type ListaRespaldosAdministrativos = {
  items: RespaldoAdministrativo[];
  total: number;
  page: number;
  page_size: number;
};
