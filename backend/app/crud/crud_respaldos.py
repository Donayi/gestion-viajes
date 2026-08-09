from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import (
    ConfirmacionRestauracionControl,
    EstadoSistemaControl,
    OperacionRespaldoControl,
    RespaldoControl,
    TicketDescargaControl,
    ValidacionRespaldoControl,
    WorkerRespaldoControl,
)


MAINTENANCE_STATE_KEY = "MANTENIMIENTO_RESTAURACION"
_UNSET = object()
RESPALDO_UPDATE_FIELDS = frozenset(
    {
        "estado",
        "sha256",
        "size_bytes",
        "table_count",
        "row_count",
        "manifest_json",
        "postgres_version",
        "application_version",
        "started_at",
        "completed_at",
        "validated_at",
        "error_codigo",
        "error_detalle",
        "eliminado_at",
    }
)


def create_respaldo(db: Session, **values: object) -> RespaldoControl:
    respaldo = RespaldoControl(**values)
    db.add(respaldo)
    db.commit()
    db.refresh(respaldo)
    return respaldo


def get_respaldo_by_id(db: Session, respaldo_id: UUID) -> RespaldoControl | None:
    return db.get(RespaldoControl, respaldo_id)


def update_respaldo(
    db: Session,
    respaldo: RespaldoControl,
    **values: object,
) -> RespaldoControl:
    for field, value in values.items():
        if field not in RESPALDO_UPDATE_FIELDS:
            raise ValueError(f"Campo de respaldo no permitido: {field}")
        setattr(respaldo, field, value)
    db.commit()
    db.refresh(respaldo)
    return respaldo


def list_respaldos(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RespaldoControl], int]:
    query = db.query(RespaldoControl)
    total = query.count()
    items = (
        query.order_by(RespaldoControl.created_at.desc(), RespaldoControl.id_respaldo.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def has_automatic_backup_in_period(
    db: Session,
    *,
    start: datetime,
    end: datetime,
) -> bool:
    return (
        db.query(RespaldoControl.id_respaldo)
        .filter(
            RespaldoControl.origen == "AUTOMATICO",
            RespaldoControl.created_at >= start,
            RespaldoControl.created_at < end,
        )
        .first()
        is not None
    )


def create_operacion(db: Session, **values: object) -> OperacionRespaldoControl:
    operacion = OperacionRespaldoControl(**values)
    db.add(operacion)
    db.commit()
    db.refresh(operacion)
    return operacion


def get_operacion_by_id(db: Session, operacion_id: UUID) -> OperacionRespaldoControl | None:
    return db.get(OperacionRespaldoControl, operacion_id)


def update_operacion(
    db: Session,
    operacion: OperacionRespaldoControl,
    *,
    estado: str | None = None,
    heartbeat_at: datetime | None | object = _UNSET,
    resultado_json: dict | None | object = _UNSET,
    resultado_restauracion: str | None | object = _UNSET,
    error_codigo: str | None | object = _UNSET,
    error_detalle: str | None | object = _UNSET,
    completed_at: datetime | None | object = _UNSET,
) -> OperacionRespaldoControl:
    updates = {
        "heartbeat_at": heartbeat_at,
        "resultado_json": resultado_json,
        "resultado_restauracion": resultado_restauracion,
        "error_codigo": error_codigo,
        "error_detalle": error_detalle,
        "completed_at": completed_at,
    }
    if estado is not None:
        operacion.estado = estado
    for field, value in updates.items():
        if value is not _UNSET:
            setattr(operacion, field, value)
    db.commit()
    db.refresh(operacion)
    return operacion


def create_validacion(db: Session, **values: object) -> ValidacionRespaldoControl:
    validacion = ValidacionRespaldoControl(**values)
    db.add(validacion)
    db.commit()
    db.refresh(validacion)
    return validacion


def get_validacion_vigente(
    db: Session,
    *,
    respaldo_id: UUID,
    sha256: str,
    now: datetime | None = None,
) -> ValidacionRespaldoControl | None:
    current_time = now or datetime.now(UTC)
    return (
        db.query(ValidacionRespaldoControl)
        .filter(
            ValidacionRespaldoControl.id_respaldo == respaldo_id,
            ValidacionRespaldoControl.sha256 == sha256,
            ValidacionRespaldoControl.estado == "VALIDO",
            ValidacionRespaldoControl.expires_at > current_time,
        )
        .order_by(ValidacionRespaldoControl.created_at.desc())
        .first()
    )


def get_estado_mantenimiento(db: Session) -> EstadoSistemaControl | None:
    return db.get(EstadoSistemaControl, MAINTENANCE_STATE_KEY)


def set_estado_mantenimiento(
    db: Session,
    *,
    activo: bool,
    mensaje_publico: str,
    id_operacion: UUID | None = None,
    updated_at: datetime | None = None,
) -> EstadoSistemaControl:
    estado = get_estado_mantenimiento(db)
    if estado is None:
        estado = EstadoSistemaControl(clave=MAINTENANCE_STATE_KEY)
        db.add(estado)
    estado.activo = activo
    estado.id_operacion = id_operacion
    estado.mensaje_publico = mensaje_publico
    estado.updated_at = updated_at or datetime.now(UTC)
    db.commit()
    db.refresh(estado)
    return estado


def register_worker_heartbeat(
    db: Session,
    *,
    worker_id: str,
    started_at: datetime,
    heartbeat_at: datetime,
    estado: str,
    application_version: str | None = None,
    postgres_tools_version: str | None = None,
    id_operacion_actual: UUID | None = None,
) -> WorkerRespaldoControl:
    worker = db.get(WorkerRespaldoControl, worker_id)
    if worker is None:
        worker = WorkerRespaldoControl(worker_id=worker_id, started_at=started_at)
        db.add(worker)
    worker.last_heartbeat_at = heartbeat_at
    worker.application_version = application_version
    worker.postgres_tools_version = postgres_tools_version
    worker.estado = estado
    worker.id_operacion_actual = id_operacion_actual
    db.commit()
    db.refresh(worker)
    return worker


def create_ticket_descarga(db: Session, **values: object) -> TicketDescargaControl:
    ticket = TicketDescargaControl(**values)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def consume_ticket_descarga(
    db: Session,
    *,
    token_hash: str,
    now: datetime | None = None,
) -> TicketDescargaControl | None:
    current_time = now or datetime.now(UTC)
    ticket = (
        db.query(TicketDescargaControl)
        .filter(
            TicketDescargaControl.token_hash == token_hash,
            TicketDescargaControl.consumed_at.is_(None),
            TicketDescargaControl.expires_at > current_time,
        )
        .with_for_update()
        .first()
    )
    if ticket is None:
        return None
    ticket.consumed_at = current_time
    db.commit()
    db.refresh(ticket)
    return ticket


def create_confirmacion_restauracion(
    db: Session,
    **values: object,
) -> ConfirmacionRestauracionControl:
    confirmacion = ConfirmacionRestauracionControl(**values)
    db.add(confirmacion)
    db.commit()
    db.refresh(confirmacion)
    return confirmacion


def consume_confirmacion_restauracion(
    db: Session,
    *,
    token_hash: str,
    now: datetime | None = None,
) -> ConfirmacionRestauracionControl | None:
    current_time = now or datetime.now(UTC)
    confirmacion = (
        db.query(ConfirmacionRestauracionControl)
        .filter(
            ConfirmacionRestauracionControl.token_hash == token_hash,
            ConfirmacionRestauracionControl.consumed_at.is_(None),
            ConfirmacionRestauracionControl.expires_at > current_time,
        )
        .with_for_update()
        .first()
    )
    if confirmacion is None:
        return None
    confirmacion.consumed_at = current_time
    db.commit()
    db.refresh(confirmacion)
    return confirmacion


__all__ = [
    "MAINTENANCE_STATE_KEY",
    "RESPALDO_UPDATE_FIELDS",
    "consume_confirmacion_restauracion",
    "consume_ticket_descarga",
    "create_confirmacion_restauracion",
    "create_operacion",
    "create_respaldo",
    "create_ticket_descarga",
    "create_validacion",
    "get_estado_mantenimiento",
    "get_operacion_by_id",
    "get_respaldo_by_id",
    "get_validacion_vigente",
    "has_automatic_backup_in_period",
    "list_respaldos",
    "register_worker_heartbeat",
    "set_estado_mantenimiento",
    "update_respaldo",
    "update_operacion",
]
