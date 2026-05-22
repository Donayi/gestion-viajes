export type TelegramDestinatario = {
  id_destinatario: number;
  nombre: string;
  chat_id: string;
  activo: boolean;
  recibe_documentos: boolean;
  recibe_mantenimiento: boolean;
  recibe_viajes: boolean;
  created_at: string;
  updated_at: string;
};

export type CreateTelegramDestinatarioPayload = {
  nombre: string;
  chat_id: string;
  activo: boolean;
  recibe_documentos: boolean;
  recibe_mantenimiento: boolean;
  recibe_viajes: boolean;
};

export type UpdateTelegramDestinatarioPayload = Partial<CreateTelegramDestinatarioPayload>;

export type TelegramTestResponse = {
  enviado: boolean;
  mensaje: string;
  destinatario: TelegramDestinatario;
};

export type ProcesarNotificacionesResponse = {
  alertas_evaluadas: number;
  alertas_enviadas: number;
  alertas_sin_destinatario: number;
  alertas_omitidas: number;
  alertas_fallidas: number;
};
