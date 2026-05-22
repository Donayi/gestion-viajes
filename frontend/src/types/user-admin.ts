export type AdminUser = {
  id_usuario: number;
  username: string;
  nombre: string;
  apellido: string;
  fecha_nacimiento: string | null;
  telefono: string | null;
  activo: boolean;
  id_rol: number;
  created_at: string;
  updated_at: string;
};

export type CreateAdminUserPayload = {
  username: string;
  password: string;
  nombre: string;
  apellido: string;
  fecha_nacimiento?: string | null;
  telefono?: string | null;
  activo: boolean;
  id_rol: number;
};

export type UpdateAdminUserPayload = {
  username?: string | null;
  nombre?: string | null;
  apellido?: string | null;
  fecha_nacimiento?: string | null;
  telefono?: string | null;
  activo?: boolean;
  id_rol?: number | null;
};

export type ChangeUserPasswordPayload = {
  new_password: string;
};
