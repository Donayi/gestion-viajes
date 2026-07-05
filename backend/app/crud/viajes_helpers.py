from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.models import (
    AsignacionViaje,
    CatalogoEstatusViaje,
    EventoOperativoViaje,
    HistorialEstatusViaje,
    Viaje,
)
from app.schemas.evento_operativo import (
    EventoOperativoCargaPayload,
    EventoOperativoRetrasoPayload,
    EventoOperativoViajePayload,
    TipoEventoOperativo,
)


def _generate_next_viaje_folio(db: Session, year: int) -> str:
    prefix = f"VJ-{year}-"
    pattern = re.compile(rf"^VJ-{year}-(\d{{4}})$")
    ultimo_folio = (
        db.query(Viaje.folio)
        .filter(Viaje.folio.like(f"{prefix}%"))
        .order_by(Viaje.folio.desc())
        .first()
    )

    consecutivo = 1
    if ultimo_folio and ultimo_folio[0]:
        match = pattern.match(ultimo_folio[0])
        if match:
            consecutivo = int(match.group(1)) + 1

    if consecutivo > 9999:
        raise ValueError(f"Se alcanzó el máximo de folios para el año {year}.")

    return f"{prefix}{consecutivo:04d}"


def _viaje_tiene_evento_operativo(
    db: Session,
    viaje_id: int,
    tipo_evento: str,
) -> bool:
    return (
        db.query(EventoOperativoViaje.id_evento)
        .filter(
            EventoOperativoViaje.id_viaje == viaje_id,
            EventoOperativoViaje.tipo_evento == tipo_evento,
        )
        .first()
        is not None
    )


def _get_ultimo_evento_operativo_por_tipo(
    db: Session,
    viaje_id: int,
    tipo_evento: str,
) -> EventoOperativoViaje | None:
    return (
        db.query(EventoOperativoViaje)
        .filter(
            EventoOperativoViaje.id_viaje == viaje_id,
            EventoOperativoViaje.tipo_evento == tipo_evento,
        )
        .order_by(EventoOperativoViaje.created_at.desc(), EventoOperativoViaje.id_evento.desc())
        .first()
    )


def _get_ultimo_evento_standby_relacionado(
    db: Session,
    viaje_id: int,
) -> EventoOperativoViaje | None:
    return (
        db.query(EventoOperativoViaje)
        .filter(
            EventoOperativoViaje.id_viaje == viaje_id,
            EventoOperativoViaje.tipo_evento.in_(["STANDBY_SOLICITADO", "STANDBY"]),
        )
        .order_by(EventoOperativoViaje.created_at.desc(), EventoOperativoViaje.id_evento.desc())
        .first()
    )


def get_solicitud_standby_pendiente(
    db: Session,
    db_viaje: Viaje,
) -> EventoOperativoViaje | None:
    ultimo_evento = _get_ultimo_evento_standby_relacionado(db, db_viaje.id_viaje)
    if not ultimo_evento:
        return None

    if ultimo_evento.tipo_evento != "STANDBY_SOLICITADO":
        return None

    estatus_actual = (
        db.query(CatalogoEstatusViaje)
        .filter(CatalogoEstatusViaje.id_estatus == db_viaje.id_estatus_actual)
        .first()
    )
    if estatus_actual and estatus_actual.clave == "STANDBY":
        return None

    solicitud_timestamp = ultimo_evento.created_at

    estatus_atendido = (
        db.query(HistorialEstatusViaje)
        .join(CatalogoEstatusViaje, HistorialEstatusViaje.id_estatus == CatalogoEstatusViaje.id_estatus)
        .filter(
            HistorialEstatusViaje.id_viaje == db_viaje.id_viaje,
            CatalogoEstatusViaje.clave.in_(["STANDBY", "ASIGNADO"]),
            HistorialEstatusViaje.changed_at > solicitud_timestamp,
        )
        .order_by(HistorialEstatusViaje.changed_at.desc(), HistorialEstatusViaje.id_historial.desc())
        .first()
    )
    if estatus_atendido:
        return None

    reasignacion_posterior = (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_viaje == db_viaje.id_viaje,
            AsignacionViaje.fecha_asignacion > solicitud_timestamp,
        )
        .order_by(AsignacionViaje.fecha_asignacion.desc(), AsignacionViaje.id_asignacion.desc())
        .first()
    )
    if reasignacion_posterior:
        return None

    reinicio_posterior = (
        db.query(EventoOperativoViaje)
        .filter(
            EventoOperativoViaje.id_viaje == db_viaje.id_viaje,
            EventoOperativoViaje.tipo_evento == "REINICIO_VIAJE",
            EventoOperativoViaje.created_at > solicitud_timestamp,
        )
        .order_by(EventoOperativoViaje.created_at.desc(), EventoOperativoViaje.id_evento.desc())
        .first()
    )
    if reinicio_posterior:
        return None

    return ultimo_evento


def _obtener_ultimo_kilometraje_por_trailer_en_viaje(
    db: Session,
    viaje_id: int,
    trailer_id: int,
):
    ultimo_evento = (
        db.query(EventoOperativoViaje)
        .filter(
            EventoOperativoViaje.id_viaje == viaje_id,
            EventoOperativoViaje.id_trailer == trailer_id,
            EventoOperativoViaje.kilometraje.is_not(None),
        )
        .order_by(
            EventoOperativoViaje.created_at.desc(),
            EventoOperativoViaje.id_evento.desc(),
        )
        .first()
    )
    return ultimo_evento.kilometraje if ultimo_evento else None


def _validar_kilometraje_monotonico_por_trailer(
    db: Session,
    db_viaje: Viaje,
    kilometraje,
) -> None:
    trailer_id = db_viaje.id_trailer_actual
    if trailer_id is None:
        raise ValueError("No hay tráiler asignado para registrar kilometraje.")

    ultimo_kilometraje = _obtener_ultimo_kilometraje_por_trailer_en_viaje(
        db,
        db_viaje.id_viaje,
        trailer_id,
    )
    if ultimo_kilometraje is None:
        return

    if kilometraje <= ultimo_kilometraje:
        raise ValueError(
            f"El kilometraje debe ser mayor al último registrado para este tráiler: {ultimo_kilometraje}."
        )


def _validar_payload_operativo_por_accion(
    db: Session,
    db_viaje: Viaje,
    tipo_evento: TipoEventoOperativo,
    payload: EventoOperativoCargaPayload | EventoOperativoRetrasoPayload | EventoOperativoViajePayload,
) -> None:
    if not payload.ubicacion or not payload.ubicacion.strip():
        raise ValueError("La ubicacion es obligatoria para esta accion")

    if payload.latitud is None or payload.longitud is None:
        raise ValueError("Debes proporcionar ubicación con latitud y longitud para continuar.")

    kilometraje = getattr(payload, "kilometraje", None)
    nivel_diesel = getattr(payload, "nivel_diesel", None)
    requiere_metricas_operativas = tipo_evento in {
        "INICIO_VIAJE",
        "REINICIO_VIAJE",
        "STANDBY_SOLICITADO",
        "STANDBY",
        "FINALIZACION_VIAJE",
    }

    if requiere_metricas_operativas and kilometraje is None:
        raise ValueError("El kilometraje es obligatorio para esta accion")

    if requiere_metricas_operativas and nivel_diesel is None:
        raise ValueError("El nivel de diesel es obligatorio para esta accion")

    if kilometraje is not None and kilometraje < 0:
        raise ValueError("El kilometraje debe ser mayor o igual a 0")

    if nivel_diesel is not None and (nivel_diesel < 0 or nivel_diesel > 100):
        raise ValueError("El nivel de diesel debe estar entre 0 y 100")

    if kilometraje is not None:
        _validar_kilometraje_monotonico_por_trailer(db, db_viaje, kilometraje)

    if isinstance(payload, EventoOperativoRetrasoPayload) and (
        not payload.comentario or not payload.comentario.strip()
    ):
        raise ValueError("El comentario es obligatorio para marcar retraso")


def _viaje_listo_para_reinicio(db: Session, db_viaje: Viaje) -> bool:
    estatus_actual = (
        db.query(CatalogoEstatusViaje)
        .filter(CatalogoEstatusViaje.id_estatus == db_viaje.id_estatus_actual)
        .first()
    )
    if not estatus_actual or estatus_actual.clave != "ASIGNADO":
        return False

    if db_viaje.id_operador_actual is None or db_viaje.id_trailer_actual is None:
        return False

    ultimo_inicio_viaje = _get_ultimo_evento_operativo_por_tipo(db, db_viaje.id_viaje, "INICIO_VIAJE")
    if not ultimo_inicio_viaje:
        return False

    ultimo_historial_standby = (
        db.query(HistorialEstatusViaje)
        .join(CatalogoEstatusViaje, HistorialEstatusViaje.id_estatus == CatalogoEstatusViaje.id_estatus)
        .filter(
            HistorialEstatusViaje.id_viaje == db_viaje.id_viaje,
            CatalogoEstatusViaje.clave == "STANDBY",
            HistorialEstatusViaje.changed_at > ultimo_inicio_viaje.created_at,
        )
        .order_by(HistorialEstatusViaje.changed_at.desc(), HistorialEstatusViaje.id_historial.desc())
        .first()
    )
    if not ultimo_historial_standby:
        return False

    hubo_reasignacion_post_standby = (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_viaje == db_viaje.id_viaje,
            AsignacionViaje.fecha_asignacion > ultimo_historial_standby.changed_at,
        )
        .order_by(AsignacionViaje.fecha_asignacion.desc(), AsignacionViaje.id_asignacion.desc())
        .first()
    )
    if not hubo_reasignacion_post_standby:
        return False

    ultimo_reinicio = _get_ultimo_evento_operativo_por_tipo(db, db_viaje.id_viaje, "REINICIO_VIAJE")
    if not ultimo_reinicio:
        return True

    return ultimo_reinicio.created_at < ultimo_historial_standby.changed_at
