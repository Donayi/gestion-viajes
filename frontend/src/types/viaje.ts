import type { EvidenciaResponse } from "@/types/evidencia";

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
  folio_viaje_cliente: string | null;
  id_cliente: number;
  lugar_inicio: string;
  lugar_destino: string;
  lugar_inicio_latitud: number | null;
  lugar_inicio_longitud: number | null;
  lugar_destino_latitud: number | null;
  lugar_destino_longitud: number | null;
  tipo_carga: string | null;
  descripcion_carga: string | null;
  id_estatus_actual: number;
  id_operador_actual: number | null;
  id_trailer_actual: number | null;
  id_caja_actual: number | null;
  fecha_programada_salida: string | null;
  fecha_carga: string | null;
  hora_carga: string | null;
  fecha_descarga: string | null;
  hora_descarga: string | null;
  fecha_inicio: string | null;
  fecha_llegada: string | null;
  fecha_entrega: string | null;
  hora_entrega: string | null;
  hora_cita_descarga: string | null;
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
  solicitud_standby_pendiente: boolean;
  requiere_reinicio_viaje: boolean;
  eventos_operativos: EventoOperativoViaje[];
};

export type UltimaUbicacionViajeMapa = {
  latitud: number | null;
  longitud: number | null;
  ubicacion: string | null;
  tipo_evento: string | null;
  created_at: string | null;
};

export type ViajeMapaItem = {
  id_viaje: number;
  folio: string;
  folio_viaje_cliente: string | null;
  cliente: ClienteResumen;
  estatus_actual: EstatusViajeResumen;
  operador_actual: OperadorResumen | null;
  trailer_actual: TrailerResumen | null;
  caja_actual: CajaResumen | null;
  lugar_inicio: string;
  lugar_destino: string;
  lugar_inicio_latitud: number | null;
  lugar_inicio_longitud: number | null;
  lugar_destino_latitud: number | null;
  lugar_destino_longitud: number | null;
  ultima_ubicacion: UltimaUbicacionViajeMapa | null;
  fecha_carga: string | null;
  hora_carga: string | null;
  fecha_descarga: string | null;
  hora_descarga: string | null;
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

export type WorkflowLocationPayload = {
  ubicacion: string;
  latitud?: number | null;
  longitud?: number | null;
  comentario?: string | null;
  evidencias?: EvidenciaOperativaInput[];
};

export type EvidenciaOperativaInput = {
  id_tipo_evidencia: number;
  id_archivo: number;
  comentario?: string | null;
  latitud?: number | null;
  longitud?: number | null;
};

export type ViajeRecord = {
  id_viaje: number;
  folio: string;
  folio_viaje_cliente: string | null;
  id_cliente: number;
  lugar_inicio: string;
  lugar_destino: string;
  lugar_inicio_latitud: number | null;
  lugar_inicio_longitud: number | null;
  lugar_destino_latitud: number | null;
  lugar_destino_longitud: number | null;
  tipo_carga: string | null;
  descripcion_carga: string | null;
  id_estatus_actual: number;
  id_operador_actual: number | null;
  id_trailer_actual: number | null;
  id_caja_actual: number | null;
  fecha_programada_salida: string | null;
  fecha_carga: string | null;
  hora_carga: string | null;
  fecha_descarga: string | null;
  hora_descarga: string | null;
  fecha_inicio: string | null;
  fecha_llegada: string | null;
  fecha_entrega: string | null;
  hora_entrega: string | null;
  hora_cita_descarga: string | null;
  observaciones: string | null;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
};

export type ViajeCreatePayload = {
  folio_viaje_cliente?: string | null;
  id_cliente: number;
  lugar_inicio: string;
  lugar_destino: string;
  lugar_inicio_latitud?: number | null;
  lugar_inicio_longitud?: number | null;
  lugar_destino_latitud?: number | null;
  lugar_destino_longitud?: number | null;
  tipo_carga?: string | null;
  descripcion_carga?: string | null;
  fecha_programada_salida?: string | null;
  fecha_carga?: string | null;
  hora_carga?: string | null;
  fecha_descarga?: string | null;
  hora_descarga?: string | null;
  hora_cita_descarga?: string | null;
  observaciones?: string | null;
};

export type ViajeUpdatePayload = {
  folio?: string | null;
  folio_viaje_cliente?: string | null;
  id_cliente?: number | null;
  lugar_inicio?: string | null;
  lugar_destino?: string | null;
  lugar_inicio_latitud?: number | null;
  lugar_inicio_longitud?: number | null;
  lugar_destino_latitud?: number | null;
  lugar_destino_longitud?: number | null;
  tipo_carga?: string | null;
  descripcion_carga?: string | null;
  fecha_programada_salida?: string | null;
  fecha_carga?: string | null;
  hora_carga?: string | null;
  fecha_descarga?: string | null;
  hora_descarga?: string | null;
  fecha_entrega?: string | null;
  hora_entrega?: string | null;
  hora_cita_descarga?: string | null;
  observaciones?: string | null;
  updated_by?: number | null;
};

export type ViajeAsignacionRecord = {
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
};

export type ViajeAsignacionCreatePayload = {
  id_operador: number;
  id_trailer: number;
  id_caja?: number | null;
  created_by?: number | null;
  motivo?: string | null;
  comentario?: string | null;
};

export type ViajeReasignacionCreatePayload = ViajeAsignacionCreatePayload;

export type OperadorDisponible = {
  id_operador: number;
  alias: string;
};

export type TrailerDisponible = {
  id_trailer: number;
  numero_economico: string;
  placas: string;
};

export type CajaDisponible = {
  id_caja: number;
  numero_economico: string | null;
  placas: string;
};

export type DisponibilidadViajeActual = {
  id_viaje: number;
  folio: string;
  estatus_clave: string | null;
};

export type OperadorDisponibilidad = {
  id_operador: number;
  alias: string;
  username: string | null;
  nombre_completo: string | null;
  numero_licencia: string | null;
  activo: boolean;
  disponible: boolean;
  viaje_actual: DisponibilidadViajeActual | null;
  motivo_no_disponible: string | null;
};

export type TrailerDisponibilidad = {
  id_trailer: number;
  numero_economico: string;
  placas: string;
  marca: string | null;
  modelo: string | null;
  numero_serie: string | null;
  activo: boolean;
  disponible: boolean;
  viaje_actual: DisponibilidadViajeActual | null;
  motivo_no_disponible: string | null;
};

export type CajaDisponibilidad = {
  id_caja: number;
  numero_economico: string | null;
  placas: string;
  tipo_caja: string | null;
  modelo: string | null;
  numero_serie: string | null;
  activo: boolean;
  disponible: boolean;
  viaje_actual: DisponibilidadViajeActual | null;
  motivo_no_disponible: string | null;
};

export type DisponibilidadResumen = {
  operadores: OperadorDisponibilidad[];
  trailers: TrailerDisponibilidad[];
  cajas: CajaDisponibilidad[];
};

export type EventoOperativoViaje = {
  id_evento: number;
  id_viaje: number;
  id_operador: number | null;
  id_trailer: number | null;
  id_caja: number | null;
  tipo_evento:
    | "INICIO_CARGA"
    | "INICIO_VIAJE"
    | "REINICIO_VIAJE"
    | "RETRASO"
    | "STANDBY_SOLICITADO"
    | "STANDBY"
    | "FINALIZACION_VIAJE";
  kilometraje: number | null;
  nivel_diesel: number | null;
  ubicacion: string;
  latitud: number | null;
  longitud: number | null;
  comentario: string | null;
  created_by: number | null;
  created_at: string;
  operador: OperadorResumen | null;
  trailer: TrailerResumen | null;
  caja: CajaResumen | null;
  evidencias: EvidenciaResponse[];
};

export type WorkflowOperationalPayload = WorkflowLocationPayload & {
  kilometraje: number;
  nivel_diesel: number;
};

export type WorkflowActionPayload = WorkflowLocationPayload | WorkflowOperationalPayload;

export type EventoOperativoViajeUpdatePayload = {
  kilometraje?: number | null;
  nivel_diesel?: number | null;
  ubicacion?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  comentario?: string | null;
};

export type CambioEstatusResponse = {
  id_viaje: number;
  id_estatus_actual: number;
  mensaje: string;
};
