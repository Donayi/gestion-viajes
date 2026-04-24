export type ClienteResumen = {
  id_cliente: number;
  nombre_razon_social: string;
  rfc: string | null;
};

export type EstatusViajeResumen = {
  id_estatus: number;
  clave: string;
  nombre: string;
  es_terminal: boolean;
  requiere_evidencia: boolean;
};

export type OperadorResumen = {
  id_operador: number;
  alias: string;
};

export type TrailerResumen = {
  id_trailer: number;
  numero_economico: string;
  placas: string;
};

export type CajaResumen = {
  id_caja: number;
  numero_economico: string | null;
  placas: string;
};

export type UsuarioResumen = {
  id_usuario: number;
  username: string;
  nombre: string;
  apellido: string;
};

export type ViajeListItem = {
  id_viaje: number;
  folio: string;
  id_cliente: number;
  lugar_inicio: string;
  lugar_destino: string;
  tipo_carga: string | null;
  descripcion_carga: string | null;
  id_estatus_actual: number;
  id_operador_actual: number | null;
  id_trailer_actual: number | null;
  id_caja_actual: number | null;
  fecha_programada_salida: string | null;
  fecha_inicio: string | null;
  fecha_llegada: string | null;
  fecha_entrega: string | null;
  hora_entrega: string | null;
  observaciones: string | null;
  created_at: string;
  updated_at: string;
  cliente: ClienteResumen;
  estatus_actual: EstatusViajeResumen;
  operador_actual: OperadorResumen | null;
  trailer_actual: TrailerResumen | null;
  caja_actual: CajaResumen | null;
};

export type ViajeDetail = ViajeListItem & {
  usuario_creador: UsuarioResumen | null;
  usuario_actualizador: UsuarioResumen | null;
};

export type HistorialEstatusEnriched = {
  id_historial: number;
  id_viaje: number;
  id_estatus: number;
  comentario: string | null;
  changed_by: number | null;
  changed_at: string;
  estatus: EstatusViajeResumen;
  usuario_cambio: UsuarioResumen | null;
};

export type ViajeAsignacionEnriched = {
  id_asignacion: number;
  id_viaje: number;
  id_operador: number | null;
  id_trailer: number | null;
  id_caja: number | null;
  activo: boolean;
  fecha_asignacion: string;
  fecha_inicio_operacion: string | null;
  fecha_fin_asignacion: string | null;
  motivo: string | null;
  comentario: string | null;
  created_by: number | null;
  created_at: string;
  operador: OperadorResumen | null;
  trailer: TrailerResumen | null;
  caja: CajaResumen | null;
  usuario_creador: UsuarioResumen | null;
};

export type ViajeComentarioAccion = {
  changed_by?: number | null;
  comentario?: string | null;
};
