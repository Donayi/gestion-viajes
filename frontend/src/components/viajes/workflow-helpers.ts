import type { ViajeDetail } from "@/types/viaje";

type EventoOperativo = ViajeDetail["eventos_operativos"][number];
type TipoEvento = EventoOperativo["tipo_evento"];

const standbyRelatedEvents: TipoEvento[] = ["STANDBY_SOLICITADO", "STANDBY", "REINICIO_VIAJE"];

function getEventTimestamp(evento: EventoOperativo) {
  const createdAt = new Date(evento.created_at).getTime();
  return Number.isNaN(createdAt) ? 0 : createdAt;
}

export function getLatestOperationalEvent(
  eventos: ViajeDetail["eventos_operativos"],
  tipoEvento: TipoEvento
) {
  return eventos
    .filter((evento) => evento.tipo_evento === tipoEvento)
    .sort((left, right) => {
      const leftDate = getEventTimestamp(left);
      const rightDate = getEventTimestamp(right);
      if (leftDate === rightDate) {
        return right.id_evento - left.id_evento;
      }
      return rightDate - leftDate;
    })[0];
}

export function getPendingStandbyRequest(viaje: ViajeDetail) {
  if (!viaje.solicitud_standby_pendiente) {
    return null;
  }

  if (viaje.estatus_actual.clave === "STANDBY") {
    return null;
  }

  const latestRelevantEvent = viaje.eventos_operativos
    .filter((evento) => standbyRelatedEvents.includes(evento.tipo_evento))
    .sort((left, right) => {
      const leftDate = getEventTimestamp(left);
      const rightDate = getEventTimestamp(right);
      if (leftDate === rightDate) {
        return right.id_evento - left.id_evento;
      }
      return rightDate - leftDate;
    })[0];

  if (!latestRelevantEvent || latestRelevantEvent.tipo_evento !== "STANDBY_SOLICITADO") {
    return null;
  }

  return latestRelevantEvent;
}
