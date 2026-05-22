export type Role = {
  id_rol: number;
  nombre: string;
  descripcion: string | null;
};

export type CreateRolePayload = {
  nombre: string;
  descripcion?: string | null;
};

export type UpdateRolePayload = {
  nombre?: string | null;
  descripcion?: string | null;
};
