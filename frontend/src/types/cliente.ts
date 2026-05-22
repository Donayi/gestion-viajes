export type Cliente = {
  id_cliente: number;
  nombre_razon_social: string;
  rfc: string | null;
  direccion: string | null;
  cp: string | null;
  regimen_fiscal: string | null;
  tiempo_credito: number | null;
  contacto_nombre: string | null;
  contacto_telefono: string | null;
  contacto_email: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateClientePayload = {
  nombre_razon_social: string;
  rfc?: string | null;
  direccion?: string | null;
  cp?: string | null;
  regimen_fiscal?: string | null;
  tiempo_credito?: number | null;
  contacto_nombre?: string | null;
  contacto_telefono?: string | null;
  contacto_email?: string | null;
  activo: boolean;
};

export type UpdateClientePayload = {
  nombre_razon_social?: string | null;
  rfc?: string | null;
  direccion?: string | null;
  cp?: string | null;
  regimen_fiscal?: string | null;
  tiempo_credito?: number | null;
  contacto_nombre?: string | null;
  contacto_telefono?: string | null;
  contacto_email?: string | null;
  activo?: boolean;
};
