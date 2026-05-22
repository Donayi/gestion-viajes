export type Operador = {
  id_operador: number;
  id_usuario: number;
  alias: string;
  numero_licencia: string | null;
  rfc: string | null;
  curp: string | null;
  numero_expediente_medico: string | null;
  licencia_vigencia: string | null;
  sua: string | null;
  sua_vigencia: string | null;
  estudio_medico: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateOperadorPayload = {
  id_usuario: number;
  alias: string;
  numero_licencia?: string | null;
  rfc?: string | null;
  curp?: string | null;
  numero_expediente_medico?: string | null;
  licencia_vigencia?: string | null;
  sua?: string | null;
  sua_vigencia?: string | null;
  estudio_medico?: string | null;
  activo: boolean;
};

export type UpdateOperadorPayload = {
  id_usuario?: number | null;
  alias?: string | null;
  numero_licencia?: string | null;
  rfc?: string | null;
  curp?: string | null;
  numero_expediente_medico?: string | null;
  licencia_vigencia?: string | null;
  sua?: string | null;
  sua_vigencia?: string | null;
  estudio_medico?: string | null;
  activo?: boolean;
};
