from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import BitacoraEvento
from app.schemas.bitacora import BitacoraEventoCreateInternal


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def create_bitacora_evento(
    db: Session,
    evento_in: BitacoraEventoCreateInternal,
) -> BitacoraEvento:
    actor = evento_in.actor
    entidad = evento_in.entidad
    evento = BitacoraEvento(
        evento_relacionado_id=evento_in.evento_relacionado_id,
        categoria=evento_in.categoria.value,
        actor_tipo=actor.tipo.value,
        usuario_id=actor.usuario_id,
        actor_username_snapshot=actor.username_snapshot,
        actor_username_normalizado=evento_in.actor_username_normalizado,
        actor_nombre_snapshot=actor.nombre_snapshot,
        actor_rol_snapshot=actor.rol_snapshot,
        modulo=evento_in.modulo,
        accion=evento_in.accion,
        resultado=evento_in.resultado.value,
        entidad_tipo=entidad.entidad_tipo if entidad is not None else None,
        entidad_id=entidad.entidad_id if entidad is not None else None,
        request_id=evento_in.request_id,
        correlation_id=evento_in.correlation_id,
        metodo_http=evento_in.metodo_http,
        ruta_template=evento_in.ruta_template,
        ip_hash=evento_in.ip_hash,
        ip_hash_version=evento_in.ip_hash_version,
        user_agent=evento_in.user_agent,
        valores_anteriores=evento_in.valores_anteriores,
        valores_posteriores=evento_in.valores_posteriores,
        datos_evento=evento_in.datos_evento,
        error_codigo=evento_in.error_codigo,
        error_mensaje=evento_in.error_mensaje,
        schema_version=evento_in.schema_version,
    )
    if evento_in.ocurrido_at is not None:
        evento.ocurrido_at = evento_in.ocurrido_at
    if evento_in.retener_hasta is not None:
        evento.retener_hasta = evento_in.retener_hasta
    db.add(evento)
    db.flush()
    return evento


def get_bitacora_evento_by_id(
    db: Session,
    evento_id: UUID,
) -> BitacoraEvento | None:
    return db.get(BitacoraEvento, evento_id)


def list_bitacora_eventos(
    db: Session,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    fecha_inicial: datetime | None = None,
    fecha_final: datetime | None = None,
    categoria: str | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    resultado: str | None = None,
    usuario_id: int | None = None,
    actor_username_normalizado: str | None = None,
    entidad_tipo: str | None = None,
    entidad_id: str | None = None,
    request_id: UUID | None = None,
) -> tuple[list[BitacoraEvento], int]:
    if page < 1:
        raise ValueError("page debe ser al menos 1")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValueError(f"page_size debe estar entre 1 y {MAX_PAGE_SIZE}")

    query = db.query(BitacoraEvento)
    if fecha_inicial is not None:
        query = query.filter(BitacoraEvento.ocurrido_at >= fecha_inicial)
    if fecha_final is not None:
        query = query.filter(BitacoraEvento.ocurrido_at <= fecha_final)
    if categoria is not None:
        query = query.filter(BitacoraEvento.categoria == categoria)
    if modulo is not None:
        query = query.filter(BitacoraEvento.modulo == modulo)
    if accion is not None:
        query = query.filter(BitacoraEvento.accion == accion)
    if resultado is not None:
        query = query.filter(BitacoraEvento.resultado == resultado)
    if usuario_id is not None:
        query = query.filter(BitacoraEvento.usuario_id == usuario_id)
    if actor_username_normalizado is not None:
        query = query.filter(
            BitacoraEvento.actor_username_normalizado == actor_username_normalizado
        )
    if entidad_tipo is not None:
        query = query.filter(BitacoraEvento.entidad_tipo == entidad_tipo)
    if entidad_id is not None:
        query = query.filter(BitacoraEvento.entidad_id == entidad_id)
    if request_id is not None:
        query = query.filter(BitacoraEvento.request_id == request_id)

    total = query.count()
    items = (
        query.order_by(
            BitacoraEvento.ocurrido_at.desc(),
            BitacoraEvento.id_evento.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "create_bitacora_evento",
    "get_bitacora_evento_by_id",
    "list_bitacora_eventos",
]
