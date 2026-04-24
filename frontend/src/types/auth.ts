export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type CurrentUser = {
  id_usuario: number;
  username: string;
  nombre: string;
  apellido: string;
  rol: string;
  id_operador: number | null;
};

export type LoginPayload = {
  username: string;
  password: string;
};
