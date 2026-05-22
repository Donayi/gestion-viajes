from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.models import Alerta, Documento, Mantenimiento, Operador, TelegramDestinatario, TipoDocumento, Viaje
from app.services.telegram_service import send_telegram_message


def get_alertas(
    db: Session,
    tipo_alerta: str | None = None,
    nivel: str | None = None,
) -> list[Alerta]:
    query = db.query(Alerta)
    if tipo_alerta:
        query = query.filter(Alerta.tipo_alerta == tipo_alerta)
    if nivel:
        query = query.filter(Alerta.nivel == nivel)
    return query.order_by(Alerta.leida.asc(), Alerta.created_at.desc(), Alerta.id_alerta.desc()).all()


def get_alerta_by_id(db: Session, alerta_id: int) -> Alerta | None:
    return db.query(Alerta).filter(Alerta.id_alerta == alerta_id).first()


def mark_alerta_as_read(db: Session, alerta: Alerta) -> Alerta:
    alerta.leida = True
    db.commit()
    db.refresh(alerta)
    return alerta


def _alerta_activa_equivalente_exists(
    db: Session,
    tipo_alerta: str,
    entidad_tipo: str,
    entidad_id: int,
    mensaje: str,
    nivel: str,
) -> bool:
    existing = db.query(Alerta.id_alerta).filter(
        Alerta.tipo_alerta == tipo_alerta,
        Alerta.entidad_tipo == entidad_tipo,
        Alerta.entidad_id == entidad_id,
        Alerta.mensaje == mensaje,
        Alerta.nivel == nivel,
        (Alerta.leida.is_(False) | Alerta.notificada.is_(False)),
    ).first()
    return existing is not None


def _build_documento_label(documento: Documento) -> str:
    tipo_nombre = documento.tipo_documento.nombre if documento.tipo_documento else "Documento"
    if documento.operador is not None:
        nombre = f"{documento.operador.usuario.nombre} {documento.operador.usuario.apellido}".strip()
        return f"{tipo_nombre} del operador {nombre}"
    if documento.trailer is not None:
        return f"{tipo_nombre} del tráiler {documento.trailer.numero_economico}"
    if documento.caja is not None:
        return f"{tipo_nombre} de la caja {documento.caja.numero_economico or documento.caja.placas}"
    return tipo_nombre


def _build_mantenimiento_label(mantenimiento: Mantenimiento) -> str:
    entidad = mantenimiento.entidad
    if isinstance(entidad, dict) and entidad.get("etiqueta"):
        return str(entidad["etiqueta"])
    return f"{mantenimiento.entidad_tipo} #{mantenimiento.entidad_id}"


def _create_alerta_if_needed(
    db: Session,
    *,
    tipo_alerta: str,
    entidad_tipo: str,
    entidad_id: int,
    mensaje: str,
    nivel: str,
    requiere_notificacion: bool,
    created_alerts: list[Alerta],
) -> bool:
    if _alerta_activa_equivalente_exists(db, tipo_alerta, entidad_tipo, entidad_id, mensaje, nivel):
        return False

    alerta = Alerta(
        tipo_alerta=tipo_alerta,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        mensaje=mensaje,
        nivel=nivel,
        leida=False,
        requiere_notificacion=requiere_notificacion,
        notificada=False,
    )
    db.add(alerta)
    created_alerts.append(alerta)
    return True


def create_alerta_evento(
    db: Session,
    *,
    tipo_alerta: str,
    entidad_tipo: str,
    entidad_id: int,
    mensaje: str,
    nivel: str,
    requiere_notificacion: bool,
) -> Alerta:
    alerta = Alerta(
        tipo_alerta=tipo_alerta,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        mensaje=mensaje,
        nivel=nivel,
        leida=False,
        requiere_notificacion=requiere_notificacion,
        notificada=False,
    )
    db.add(alerta)
    return alerta


def _procesar_alerta_telegram(db: Session, alerta: Alerta) -> bool:
    if not alerta.requiere_notificacion or alerta.notificada:
        return False

    destinatarios = _get_destinatarios_para_alerta(db, alerta)
    if not destinatarios:
        if settings.telegram_default_chat_id:
            destinatarios = [
                TelegramDestinatario(
                    id_destinatario=0,
                    nombre="Canal por defecto",
                    chat_id=settings.telegram_default_chat_id,
                    activo=True,
                    recibe_documentos=True,
                    recibe_mantenimiento=True,
                    recibe_viajes=True,
                )
            ]
        else:
            return False

    message = _format_alerta_message(alerta)
    sent_any = False
    for destinatario in destinatarios:
        if not destinatario.chat_id:
            continue
        if send_telegram_message(message, chat_id=destinatario.chat_id):
            sent_any = True

    if sent_any:
        alerta.notificada = True
        alerta.canal_notificacion = "TELEGRAM"
        alerta.fecha_notificacion = datetime.utcnow()
        db.commit()
        db.refresh(alerta)
        return True

    db.rollback()
    return False


def notificar_alerta_inmediata_si_aplica(db: Session, alerta: Alerta | None) -> bool:
    if alerta is None:
        return False

    try:
        return _procesar_alerta_telegram(db, alerta)
    except Exception:
        db.rollback()
        return False


def _resolve_alerta_channel(tipo_alerta: str) -> str | None:
    if tipo_alerta in {"DOCUMENTO_POR_VENCER", "DOCUMENTO_VENCIDO"}:
        return "documentos"
    if tipo_alerta in {"MANTENIMIENTO_ENTRADA", "MANTENIMIENTO_PROXIMO"}:
        return "mantenimiento"
    if tipo_alerta in {
        "VIAJE_CREADO",
        "VIAJE_ASIGNADO",
        "VIAJE_ESTATUS_CAMBIO",
        "STANDBY_SOLICITADO",
    }:
        return "viajes"
    return None


def _get_destinatarios_para_alerta(db: Session, alerta: Alerta) -> list[TelegramDestinatario]:
    channel = _resolve_alerta_channel(alerta.tipo_alerta)
    query = db.query(TelegramDestinatario).filter(TelegramDestinatario.activo.is_(True))
    if channel == "documentos":
        query = query.filter(TelegramDestinatario.recibe_documentos.is_(True))
    elif channel == "mantenimiento":
        query = query.filter(TelegramDestinatario.recibe_mantenimiento.is_(True))
    elif channel == "viajes":
        query = query.filter(TelegramDestinatario.recibe_viajes.is_(True))
    else:
        return []
    return query.order_by(TelegramDestinatario.id_destinatario.asc()).all()


def _format_alerta_message(alerta: Alerta) -> str:
    icons = {
        "CRITICAL": "🚨",
        "WARNING": "⚠️",
        "INFO": "ℹ️",
    }
    return (
        f"{icons.get(alerta.nivel, 'ℹ️')} {alerta.tipo_alerta.replace('_', ' ')}\n"
        f"{alerta.mensaje}"
    )


def _query_documentos_vigencia(db: Session) -> list[Documento]:
    return (
        db.query(Documento)
        .options(
            joinedload(Documento.tipo_documento),
            joinedload(Documento.operador).joinedload(Operador.usuario),
            joinedload(Documento.trailer),
            joinedload(Documento.caja),
        )
        .filter(
            Documento.activo.is_(True),
            Documento.fecha_expiracion.is_not(None),
            (
                Documento.id_operador.is_not(None)
                | Documento.id_trailer.is_not(None)
                | Documento.id_caja.is_not(None)
            ),
        )
        .all()
    )


def _query_mantenimientos_activos(db: Session) -> list[Mantenimiento]:
    active_statuses = {"ABIERTO", "EN_PROCESO"}
    return (
        db.query(Mantenimiento)
        .options(
            joinedload(Mantenimiento.trailer),
            joinedload(Mantenimiento.caja),
        )
        .filter(Mantenimiento.estatus.in_(active_statuses))
        .all()
    )


def generar_alertas(db: Session) -> dict[str, object]:
    today = date.today()
    soon_limit = today + timedelta(days=3)

    created_alerts: list[Alerta] = []
    skipped_duplicates = 0

    documentos = _query_documentos_vigencia(db)
    for documento in documentos:
        if documento.fecha_expiracion is None:
            continue

        label = _build_documento_label(documento)
        entidad_tipo = documento.entidad_tipo or "DOCUMENTO"
        entidad_id = documento.entidad_id or documento.id_documento

        if documento.fecha_expiracion < today:
            created = _create_alerta_if_needed(
                db,
                tipo_alerta="DOCUMENTO_VENCIDO",
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
                mensaje=f"El documento {label} venció el {documento.fecha_expiracion.isoformat()}.",
                nivel="CRITICAL",
                requiere_notificacion=True,
                created_alerts=created_alerts,
            )
            if not created:
                skipped_duplicates += 1
        elif documento.fecha_expiracion <= soon_limit:
            created = _create_alerta_if_needed(
                db,
                tipo_alerta="DOCUMENTO_POR_VENCER",
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
                mensaje=f"El documento {label} vence el {documento.fecha_expiracion.isoformat()}.",
                nivel="WARNING",
                requiere_notificacion=True,
                created_alerts=created_alerts,
            )
            if not created:
                skipped_duplicates += 1

    mantenimientos = _query_mantenimientos_activos(db)
    for mantenimiento in mantenimientos:
        if mantenimiento.fecha_proximo_mantenimiento is None:
            continue

        label = _build_mantenimiento_label(mantenimiento)
        if mantenimiento.fecha_proximo_mantenimiento < today:
            created = _create_alerta_if_needed(
                db,
                tipo_alerta="MANTENIMIENTO_PROXIMO",
                entidad_tipo=mantenimiento.entidad_tipo,
                entidad_id=mantenimiento.entidad_id or mantenimiento.id_mantenimiento,
                mensaje=(
                    f"El mantenimiento próximo de {label} ya venció y estaba programado para "
                    f"{mantenimiento.fecha_proximo_mantenimiento.isoformat()}."
                ),
                nivel="CRITICAL",
                requiere_notificacion=True,
                created_alerts=created_alerts,
            )
            if not created:
                skipped_duplicates += 1
        elif mantenimiento.fecha_proximo_mantenimiento <= soon_limit:
            created = _create_alerta_if_needed(
                db,
                tipo_alerta="MANTENIMIENTO_PROXIMO",
                entidad_tipo=mantenimiento.entidad_tipo,
                entidad_id=mantenimiento.entidad_id or mantenimiento.id_mantenimiento,
                mensaje=(
                    f"El próximo mantenimiento de {label} está programado para "
                    f"{mantenimiento.fecha_proximo_mantenimiento.isoformat()}."
                ),
                nivel="WARNING",
                requiere_notificacion=True,
                created_alerts=created_alerts,
            )
            if not created:
                skipped_duplicates += 1

    db.commit()

    for alerta in created_alerts:
        db.refresh(alerta)

    return {
        "nuevas_alertas_creadas": len(created_alerts),
        "omitidas_por_duplicadas": skipped_duplicates,
        "alertas_creadas": created_alerts,
    }


def crear_alerta_entrada_mantenimiento(db: Session, mantenimiento: Mantenimiento) -> Alerta:
    label = _build_mantenimiento_label(mantenimiento)
    return create_alerta_evento(
        db,
        tipo_alerta="MANTENIMIENTO_ENTRADA",
        entidad_tipo=mantenimiento.entidad_tipo,
        entidad_id=mantenimiento.entidad_id or mantenimiento.id_mantenimiento,
        mensaje=(
            f"El {mantenimiento.entidad_tipo.lower()} {label} entró a mantenimiento "
            f"{mantenimiento.tipo_mantenimiento.lower()}."
        ),
        nivel="WARNING",
        requiere_notificacion=True,
    )


def crear_alerta_viaje_creado(db: Session, viaje: Viaje) -> Alerta:
    return create_alerta_evento(
        db,
        tipo_alerta="VIAJE_CREADO",
        entidad_tipo="VIAJE",
        entidad_id=viaje.id_viaje,
        mensaje=f"Se creó el viaje {viaje.folio}.",
        nivel="INFO",
        requiere_notificacion=True,
    )


def crear_alerta_cambio_estatus_viaje(
    db: Session,
    viaje: Viaje,
    estatus_origen: str,
    estatus_destino: str,
) -> Alerta:
    return create_alerta_evento(
        db,
        tipo_alerta="VIAJE_ESTATUS_CAMBIO",
        entidad_tipo="VIAJE",
        entidad_id=viaje.id_viaje,
        mensaje=f"El viaje {viaje.folio} cambió de {estatus_origen} a {estatus_destino}.",
        nivel="INFO",
        requiere_notificacion=True,
    )


def crear_alerta_asignacion_viaje(
    db: Session,
    viaje: Viaje,
    operador_nombre: str,
) -> Alerta:
    return create_alerta_evento(
        db,
        tipo_alerta="VIAJE_ASIGNADO",
        entidad_tipo="VIAJE",
        entidad_id=viaje.id_viaje,
        mensaje=f"El viaje {viaje.folio} fue asignado al operador {operador_nombre}.",
        nivel="INFO",
        requiere_notificacion=True,
    )


def crear_alerta_standby_solicitado(
    db: Session,
    viaje: Viaje,
    operador_nombre: str,
    ubicacion: str,
    comentario: str | None,
) -> Alerta:
    app_url = (settings.app_public_url or "").rstrip("/")
    link = f"{app_url}/viajes/{viaje.id_viaje}" if app_url else f"Viaje #{viaje.id_viaje}"
    mensaje = (
        "Solicitud de STANDBY\n"
        f"Viaje: {viaje.folio}\n"
        f"Operador: {operador_nombre}\n"
        f"Ubicación: {ubicacion}\n"
        f"Comentario: {comentario or 'Sin comentario'}\n"
        f"Autorizar aquí:\n{link}"
    )
    return create_alerta_evento(
        db,
        tipo_alerta="STANDBY_SOLICITADO",
        entidad_tipo="VIAJE",
        entidad_id=viaje.id_viaje,
        mensaje=mensaje,
        nivel="CRITICAL",
        requiere_notificacion=True,
    )


def procesar_notificaciones_pendientes(db: Session) -> dict[str, int]:
    alertas = (
        db.query(Alerta)
        .filter(
            Alerta.requiere_notificacion.is_(True),
            Alerta.notificada.is_(False),
        )
        .order_by(Alerta.created_at.asc(), Alerta.id_alerta.asc())
        .all()
    )

    enviadas = 0
    sin_destinatario = 0
    omitidas = 0
    fallidas = 0

    for alerta in alertas:
        if _procesar_alerta_telegram(db, alerta):
            enviadas += 1
        else:
            if _get_destinatarios_para_alerta(db, alerta) or settings.telegram_default_chat_id:
                if settings.telegram_enabled:
                    fallidas += 1
                else:
                    omitidas += 1
            else:
                sin_destinatario += 1
    return {
        "alertas_evaluadas": len(alertas),
        "alertas_enviadas": enviadas,
        "alertas_sin_destinatario": sin_destinatario,
        "alertas_omitidas": omitidas,
        "alertas_fallidas": fallidas,
    }
