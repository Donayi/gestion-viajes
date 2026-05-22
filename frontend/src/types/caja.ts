export type Caja = {
  id_caja: number;
  numero_economico: string | null;
  placas: string;
  tipo_caja: string | null;
  marca: string | null;
  modelo: string | null;
  anio: number | null;
  poliza_seguro: string | null;
  seguro_vigencia: string | null;
  tarjeta_circulacion: string | null;
  tarjeta_vigencia: string | null;
  numero_serie: string | null;
  verificacion: string | null;
  verificacion_vigencia: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateCajaPayload = {
  numero_economico?: string | null;
  placas: string;
  tipo_caja?: string | null;
  marca?: string | null;
  modelo?: string | null;
  anio?: number | null;
  poliza_seguro?: string | null;
  seguro_vigencia?: string | null;
  tarjeta_circulacion?: string | null;
  tarjeta_vigencia?: string | null;
  numero_serie?: string | null;
  verificacion?: string | null;
  verificacion_vigencia?: string | null;
  activo: boolean;
};

export type UpdateCajaPayload = {
  numero_economico?: string | null;
  placas?: string | null;
  tipo_caja?: string | null;
  marca?: string | null;
  modelo?: string | null;
  anio?: number | null;
  poliza_seguro?: string | null;
  seguro_vigencia?: string | null;
  tarjeta_circulacion?: string | null;
  tarjeta_vigencia?: string | null;
  numero_serie?: string | null;
  verificacion?: string | null;
  verificacion_vigencia?: string | null;
  activo?: boolean;
};
