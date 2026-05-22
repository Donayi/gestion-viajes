export type AlertaNivel = "INFO" | "WARNING" | "CRITICAL";

export type AlertaRecord = {
  id_alerta: number;
  tipo_alerta: string;
  entidad_tipo: string;
  entidad_id: number;
  mensaje: string;
  nivel: AlertaNivel;
  leida: boolean;
  created_at: string;
};

export type GenerarAlertasResponse = {
  nuevas_alertas_creadas: number;
  omitidas_por_duplicadas: number;
  alertas_creadas: AlertaRecord[];
};
