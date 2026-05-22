export type Trailer = {
  id_trailer: number;
  numero_economico: string;
  placas: string;
  marca: string | null;
  modelo: string | null;
  anio: number | null;
  poliza_seguro: string | null;
  seguro_vigencia: string | null;
  tarjeta_circulacion: string | null;
  tarjeta_vigencia: string | null;
  permiso_circulacion: string | null;
  numero_serie: string | null;
  verificacion: string | null;
  verificacion_vigencia: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateTrailerPayload = {
  numero_economico: string;
  placas: string;
  marca?: string | null;
  modelo?: string | null;
  anio?: number | null;
  poliza_seguro?: string | null;
  seguro_vigencia?: string | null;
  tarjeta_circulacion?: string | null;
  tarjeta_vigencia?: string | null;
  permiso_circulacion?: string | null;
  numero_serie?: string | null;
  verificacion?: string | null;
  verificacion_vigencia?: string | null;
  activo: boolean;
};

export type UpdateTrailerPayload = {
  numero_economico?: string | null;
  placas?: string | null;
  marca?: string | null;
  modelo?: string | null;
  anio?: number | null;
  poliza_seguro?: string | null;
  seguro_vigencia?: string | null;
  tarjeta_circulacion?: string | null;
  tarjeta_vigencia?: string | null;
  permiso_circulacion?: string | null;
  numero_serie?: string | null;
  verificacion?: string | null;
  verificacion_vigencia?: string | null;
  activo?: boolean;
};
