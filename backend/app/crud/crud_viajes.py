from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_

from app.models.models import (
    ArchivoStorage,
    AsignacionViaje,
    Caja,
    CatalogoEstatusViaje,
    Cliente,
    Documento,
    Evidencia,
    EventoOperativoViaje,
    HistorialEstatusViaje,
    Operador,
    Trailer,
    TipoDocumento,
    TipoEvidencia,
    TransicionEstatusViaje,
    Usuario,
    Viaje,
)
from app.core.config import settings
from app.core.storage_r2 import build_public_file_url
from app.crud.crud_alertas import (
    crear_alerta_asignacion_viaje,
    crear_alerta_cambio_estatus_viaje,
    crear_alerta_standby_solicitado,
    crear_alerta_viaje_creado,
    notificar_alerta_inmediata_si_aplica,
)
from app.crud.crud_mantenimientos import (
    caja_en_mantenimiento,
    get_mantenimientos_activos_por_tipo,
    trailer_en_mantenimiento,
)
from app.schemas.documento import DocumentoCreate
from app.schemas.evidencia import EvidenciaOperativaInput, ViajeEvidenciaCreate, ViajeEvidenciaUpdate
from app.schemas.evento_operativo import (
    EventoOperativoCargaPayload,
    EventoOperativoRetrasoPayload,
    EventoOperativoViajePayload,
    EventoOperativoViajeUpdatePayload,
    TipoEventoOperativo,
)
from app.schemas.viaje import ViajeAsignacionCreate, ViajeCambioEstatus, ViajeCreate, ViajeUpdate


def _get_operador_display_name(db: Session, operador_id: int | None) -> str:
    if operador_id is None:
        return "Sin operador"
    operador = db.query(Operador).options(joinedload(Operador.usuario)).filter(
        Operador.id_operador == operador_id
    ).first()
    if not operador:
        return f"Operador #{operador_id}"
    if operador.usuario:
        return f"{operador.usuario.nombre} {operador.usuario.apellido}".strip()
    return operador.alias


def _to_float(value):
    if value is None:
        return None
    return float(value)


def get_estatus_by_clave(db: Session, clave: str) -> CatalogoEstatusViaje | None:
    return (
        db.query(CatalogoEstatusViaje)
        .filter(CatalogoEstatusViaje.clave == clave)
        .first()
    )


def get_estatus_by_id(db: Session, estatus_id: int) -> CatalogoEstatusViaje | None:
    return (
        db.query(CatalogoEstatusViaje)
        .filter(CatalogoEstatusViaje.id_estatus == estatus_id)
        .first()
    )


def get_viaje_by_id(db: Session, viaje_id: int) -> Viaje | None:
    return db.query(Viaje).filter(Viaje.id_viaje == viaje_id).first()


def get_viaje_by_folio(db: Session, folio: str) -> Viaje | None:
    return db.query(Viaje).filter(Viaje.folio == folio).first()


def get_viajes(db: Session, skip: int = 0, limit: int = 100) -> list[Viaje]:
    return db.query(Viaje).offset(skip).limit(limit).all()


def get_viajes_visibles_para_operador(
    db: Session,
    operador_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[Viaje]:
    subquery_viajes_con_asignacion_activa = (
        db.query(AsignacionViaje.id_viaje)
        .filter(
            AsignacionViaje.id_operador == operador_id,
            AsignacionViaje.activo.is_(True),
        )
        .subquery()
    )

    return (
        db.query(Viaje)
        .options(
            joinedload(Viaje.cliente),
            joinedload(Viaje.estatus_actual),
            joinedload(Viaje.operador_actual),
            joinedload(Viaje.trailer_actual),
            joinedload(Viaje.caja_actual),
        )
        .filter(
            or_(
                Viaje.id_operador_actual == operador_id,
                Viaje.id_viaje.in_(subquery_viajes_con_asignacion_activa),
            )
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def operador_puede_ver_viaje(db: Session, operador_id: int, viaje_id: int) -> bool:
    subquery_viajes_con_asignacion_activa = (
        db.query(AsignacionViaje.id_viaje)
        .filter(
            AsignacionViaje.id_operador == operador_id,
            AsignacionViaje.activo.is_(True),
        )
        .subquery()
    )

    return (
        db.query(Viaje)
        .filter(
            Viaje.id_viaje == viaje_id,
            or_(
                Viaje.id_operador_actual == operador_id,
                Viaje.id_viaje.in_(subquery_viajes_con_asignacion_activa),
            ),
        )
        .first()
        is not None
    )


def operador_puede_operar_viaje(db: Session, operador_id: int, viaje_id: int) -> bool:
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        return False

    if db_viaje.id_operador_actual == operador_id:
        return True

    tiene_asignacion_activa = (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_viaje == viaje_id,
            AsignacionViaje.id_operador == operador_id,
            AsignacionViaje.activo.is_(True),
        )
        .first()
        is not None
    )
    if tiene_asignacion_activa:
        return True

    tuvo_asignacion_historica = (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_viaje == viaje_id,
            AsignacionViaje.id_operador == operador_id,
        )
        .first()
        is not None
    )

    if not tuvo_asignacion_historica:
        return False

    return db_viaje.id_operador_actual is None or db_viaje.id_operador_actual == operador_id


def get_viajes_enriched(db: Session, skip: int = 0, limit: int = 100) -> list[Viaje]:
    return (
        db.query(Viaje)
        .options(
            joinedload(Viaje.cliente),
            joinedload(Viaje.estatus_actual),
            joinedload(Viaje.operador_actual),
            joinedload(Viaje.trailer_actual),
            joinedload(Viaje.caja_actual),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_viajes_mapa(
    db: Session,
    estatus_claves: list[str] | None = None,
    incluir_finalizados: bool = True,
    incluir_cancelados: bool = False,
):
    query = (
        db.query(Viaje)
        .join(CatalogoEstatusViaje, Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus)
        .options(
            joinedload(Viaje.cliente),
            joinedload(Viaje.estatus_actual),
            joinedload(Viaje.operador_actual),
            joinedload(Viaje.trailer_actual),
            joinedload(Viaje.caja_actual),
        )
    )

    if estatus_claves:
        query = query.filter(CatalogoEstatusViaje.clave.in_(estatus_claves))

    if not incluir_finalizados:
        query = query.filter(CatalogoEstatusViaje.clave != "FINALIZADO")

    if not incluir_cancelados:
        query = query.filter(CatalogoEstatusViaje.clave != "CANCELADO")

    viajes = (
        query.order_by(Viaje.updated_at.desc(), Viaje.id_viaje.desc()).all()
    )

    if not viajes:
        return []

    viaje_ids = [viaje.id_viaje for viaje in viajes]
    eventos_geo = (
        db.query(EventoOperativoViaje)
        .filter(
            EventoOperativoViaje.id_viaje.in_(viaje_ids),
            EventoOperativoViaje.latitud.is_not(None),
            EventoOperativoViaje.longitud.is_not(None),
        )
        .order_by(
            EventoOperativoViaje.id_viaje.asc(),
            EventoOperativoViaje.created_at.desc(),
            EventoOperativoViaje.id_evento.desc(),
        )
        .all()
    )

    ultimo_evento_por_viaje: dict[int, EventoOperativoViaje] = {}
    for evento in eventos_geo:
        if evento.id_viaje not in ultimo_evento_por_viaje:
            ultimo_evento_por_viaje[evento.id_viaje] = evento

    viajes_mapa: list[dict] = []
    for viaje in viajes:
        ultimo_evento = ultimo_evento_por_viaje.get(viaje.id_viaje)

        ultima_ubicacion = None
        if ultimo_evento:
            ultima_ubicacion = {
                "latitud": _to_float(ultimo_evento.latitud),
                "longitud": _to_float(ultimo_evento.longitud),
                "ubicacion": ultimo_evento.ubicacion,
                "tipo_evento": ultimo_evento.tipo_evento,
                "created_at": ultimo_evento.created_at,
            }
        elif viaje.lugar_inicio_latitud is not None and viaje.lugar_inicio_longitud is not None:
            ultima_ubicacion = {
                "latitud": _to_float(viaje.lugar_inicio_latitud),
                "longitud": _to_float(viaje.lugar_inicio_longitud),
                "ubicacion": viaje.lugar_inicio,
                "tipo_evento": "ORIGEN_REFERENCIA",
                "created_at": viaje.created_at,
            }

        viajes_mapa.append(
            {
                "id_viaje": viaje.id_viaje,
                "folio": viaje.folio,
                "folio_viaje_cliente": viaje.folio_viaje_cliente,
                "cliente": viaje.cliente,
                "estatus_actual": viaje.estatus_actual,
                "operador_actual": viaje.operador_actual,
                "trailer_actual": viaje.trailer_actual,
                "caja_actual": viaje.caja_actual,
                "lugar_inicio": viaje.lugar_inicio,
                "lugar_destino": viaje.lugar_destino,
                "lugar_inicio_latitud": _to_float(viaje.lugar_inicio_latitud),
                "lugar_inicio_longitud": _to_float(viaje.lugar_inicio_longitud),
                "lugar_destino_latitud": _to_float(viaje.lugar_destino_latitud),
                "lugar_destino_longitud": _to_float(viaje.lugar_destino_longitud),
                "ultima_ubicacion": ultima_ubicacion,
                "fecha_carga": viaje.fecha_carga,
                "hora_carga": viaje.hora_carga,
                "fecha_descarga": viaje.fecha_descarga,
                "hora_descarga": viaje.hora_descarga,
            }
        )

    return viajes_mapa


def get_viaje_detail_by_id(db: Session, viaje_id: int) -> Viaje | None:
    return (
        db.query(Viaje)
        .options(
            joinedload(Viaje.cliente),
            joinedload(Viaje.estatus_actual),
            joinedload(Viaje.operador_actual),
            joinedload(Viaje.trailer_actual),
            joinedload(Viaje.caja_actual),
            joinedload(Viaje.usuario_creador),
            joinedload(Viaje.usuario_actualizador),
            selectinload(Viaje.eventos_operativos).joinedload(EventoOperativoViaje.operador),
            selectinload(Viaje.eventos_operativos).joinedload(EventoOperativoViaje.trailer),
            selectinload(Viaje.eventos_operativos).joinedload(EventoOperativoViaje.caja),
            selectinload(Viaje.eventos_operativos)
            .selectinload(EventoOperativoViaje.evidencias)
            .joinedload(Evidencia.archivo),
        )
        .filter(Viaje.id_viaje == viaje_id)
        .first()
    )


def cliente_exists(db: Session, cliente_id: int) -> bool:
    return db.query(Cliente).filter(Cliente.id_cliente == cliente_id).first() is not None


def operador_exists(db: Session, operador_id: int) -> bool:
    return db.query(Operador).filter(Operador.id_operador == operador_id).first() is not None


def trailer_exists(db: Session, trailer_id: int) -> bool:
    return db.query(Trailer).filter(Trailer.id_trailer == trailer_id).first() is not None


def caja_exists(db: Session, caja_id: int) -> bool:
    return db.query(Caja).filter(Caja.id_caja == caja_id).first() is not None


def usuario_exists(db: Session, usuario_id: int) -> bool:
    return db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first() is not None


def tipo_evidencia_exists(db: Session, tipo_evidencia_id: int) -> bool:
    return (
        db.query(TipoEvidencia)
        .filter(TipoEvidencia.id_tipo_evidencia == tipo_evidencia_id)
        .first()
        is not None
    )


def get_tipo_documento_by_id(db: Session, tipo_documento_id: int) -> TipoDocumento | None:
    return (
        db.query(TipoDocumento)
        .filter(TipoDocumento.id_tipo_documento == tipo_documento_id)
        .first()
    )


def tipo_documento_exists(db: Session, tipo_documento_id: int) -> bool:
    return get_tipo_documento_by_id(db, tipo_documento_id) is not None


def archivo_storage_exists(db: Session, archivo_id: int) -> bool:
    return (
        db.query(ArchivoStorage)
        .filter(ArchivoStorage.id_archivo == archivo_id)
        .first()
        is not None
    )


def get_tipos_evidencia(db: Session) -> list[TipoEvidencia]:
    return (
        db.query(TipoEvidencia)
        .order_by(TipoEvidencia.id_tipo_evidencia.asc())
        .all()
    )


def get_tipos_documento(db: Session) -> list[TipoDocumento]:
    return (
        db.query(TipoDocumento)
        .order_by(TipoDocumento.id_tipo_documento.asc())
        .all()
    )


def get_archivos_storage_prueba(db: Session) -> list[ArchivoStorage]:
    return (
        db.query(ArchivoStorage)
        .filter(ArchivoStorage.bucket == "mock-viajes")
        .order_by(ArchivoStorage.id_archivo.asc())
        .all()
    )


def create_archivo_storage_upload(
    db: Session,
    file_key: str,
    nombre_original: str,
    extension: str | None,
    content_type: str,
    size_bytes: int | None,
    subido_por: int | None,
) -> ArchivoStorage:
    bucket = settings.r2_bucket
    if not bucket:
        raise ValueError("Falta configurar R2_BUCKET")

    nombre_guardado = Path(file_key).name
    db_archivo = ArchivoStorage(
        proveedor="CLOUDFLARE_R2",
        bucket=bucket,
        file_key=file_key,
        nombre_original=nombre_original,
        nombre_guardado=nombre_guardado,
        extension=extension,
        content_type=content_type,
        size_bytes=size_bytes,
        url_publica=(
            build_public_file_url(file_key)
        ),
        subido_por=subido_por,
    )
    db.add(db_archivo)
    db.commit()
    db.refresh(db_archivo)
    return db_archivo


def get_evidencia_by_id(evidencia_id: int, db: Session) -> Evidencia | None:
    return db.query(Evidencia).filter(Evidencia.id_evidencia == evidencia_id).first()


def get_evidencia_by_id_and_viaje(
    db: Session,
    evidencia_id: int,
    viaje_id: int,
) -> Evidencia | None:
    return (
        db.query(Evidencia)
        .filter(
            Evidencia.id_evidencia == evidencia_id,
            Evidencia.id_viaje == viaje_id,
        )
        .first()
    )


def get_evidencias_by_viaje(db: Session, viaje_id: int) -> list[Evidencia]:
    return (
        db.query(Evidencia)
        .filter(Evidencia.id_viaje == viaje_id)
        .order_by(Evidencia.id_evidencia.desc())
        .all()
    )


def get_documentos_by_viaje(db: Session, viaje_id: int) -> list[Documento]:
    return (
        db.query(Documento)
        .options(
            joinedload(Documento.tipo_documento),
            joinedload(Documento.archivo),
        )
        .filter(Documento.id_viaje == viaje_id)
        .order_by(Documento.id_documento.desc())
        .all()
    )


def get_documentos_by_operador(db: Session, operador_id: int) -> list[Documento]:
    return (
        db.query(Documento)
        .options(
            joinedload(Documento.tipo_documento),
            joinedload(Documento.archivo),
        )
        .filter(Documento.id_operador == operador_id)
        .order_by(Documento.id_documento.desc())
        .all()
    )


def get_documentos_by_trailer(db: Session, trailer_id: int) -> list[Documento]:
    return (
        db.query(Documento)
        .options(
            joinedload(Documento.tipo_documento),
            joinedload(Documento.archivo),
        )
        .filter(Documento.id_trailer == trailer_id)
        .order_by(Documento.id_documento.desc())
        .all()
    )


def get_documentos_by_caja(db: Session, caja_id: int) -> list[Documento]:
    return (
        db.query(Documento)
        .options(
            joinedload(Documento.tipo_documento),
            joinedload(Documento.archivo),
        )
        .filter(Documento.id_caja == caja_id)
        .order_by(Documento.id_documento.desc())
        .all()
    )


def _validar_datos_documento_create(
    db: Session,
    documento_in: DocumentoCreate,
    aplica_a: str,
) -> TipoDocumento:
    tipo_documento = get_tipo_documento_by_id(db, documento_in.id_tipo_documento)
    if not tipo_documento:
        raise ValueError("El tipo de documento especificado no existe")

    if not archivo_storage_exists(db, documento_in.id_archivo):
        raise ValueError("El archivo especificado no existe")

    if documento_in.subido_por is not None and not usuario_exists(db, documento_in.subido_por):
        raise ValueError("El usuario que sube el documento no existe")

    if tipo_documento.aplica_a != aplica_a:
        raise ValueError(f"El tipo de documento no aplica a {aplica_a}")

    return tipo_documento


def create_documento_viaje(
    db: Session,
    db_viaje: Viaje,
    documento_in: DocumentoCreate,
) -> Documento:
    _validar_datos_documento_create(db, documento_in, "VIAJE")

    db_documento = Documento(
        id_tipo_documento=documento_in.id_tipo_documento,
        id_viaje=db_viaje.id_viaje,
        id_archivo=documento_in.id_archivo,
        fecha_emision=documento_in.fecha_emision,
        fecha_expiracion=documento_in.fecha_expiracion,
        estatus=documento_in.estatus,
        comentario=documento_in.comentario,
        activo=documento_in.activo,
        subido_por=documento_in.subido_por,
    )
    db.add(db_documento)
    db.commit()
    db.refresh(db_documento)
    return db_documento


def create_documento_operador_actual_viaje(
    db: Session,
    db_viaje: Viaje,
    documento_in: DocumentoCreate,
) -> Documento:
    operador_actual = db_viaje.operador_actual
    if not operador_actual:
        raise ValueError("El viaje no tiene operador actual para asociar documentos")

    _validar_datos_documento_create(db, documento_in, "OPERADOR")

    db_documento = Documento(
        id_tipo_documento=documento_in.id_tipo_documento,
        id_operador=operador_actual.id_operador,
        id_archivo=documento_in.id_archivo,
        fecha_emision=documento_in.fecha_emision,
        fecha_expiracion=documento_in.fecha_expiracion,
        estatus=documento_in.estatus,
        comentario=documento_in.comentario,
        activo=documento_in.activo,
        subido_por=documento_in.subido_por,
    )
    db.add(db_documento)
    db.commit()
    db.refresh(db_documento)
    return db_documento


def create_documento_trailer_actual_viaje(
    db: Session,
    db_viaje: Viaje,
    documento_in: DocumentoCreate,
) -> Documento:
    trailer_actual = db_viaje.trailer_actual
    if not trailer_actual:
        raise ValueError("El viaje no tiene tráiler actual para asociar documentos")

    _validar_datos_documento_create(db, documento_in, "TRAILER")

    db_documento = Documento(
        id_tipo_documento=documento_in.id_tipo_documento,
        id_trailer=trailer_actual.id_trailer,
        id_archivo=documento_in.id_archivo,
        fecha_emision=documento_in.fecha_emision,
        fecha_expiracion=documento_in.fecha_expiracion,
        estatus=documento_in.estatus,
        comentario=documento_in.comentario,
        activo=documento_in.activo,
        subido_por=documento_in.subido_por,
    )
    db.add(db_documento)
    db.commit()
    db.refresh(db_documento)
    return db_documento


def create_documento_caja_actual_viaje(
    db: Session,
    db_viaje: Viaje,
    documento_in: DocumentoCreate,
) -> Documento:
    caja_actual = db_viaje.caja_actual
    if not caja_actual:
        raise ValueError("El viaje no tiene caja actual para asociar documentos")

    _validar_datos_documento_create(db, documento_in, "CAJA")

    db_documento = Documento(
        id_tipo_documento=documento_in.id_tipo_documento,
        id_caja=caja_actual.id_caja,
        id_archivo=documento_in.id_archivo,
        fecha_emision=documento_in.fecha_emision,
        fecha_expiracion=documento_in.fecha_expiracion,
        estatus=documento_in.estatus,
        comentario=documento_in.comentario,
        activo=documento_in.activo,
        subido_por=documento_in.subido_por,
    )
    db.add(db_documento)
    db.commit()
    db.refresh(db_documento)
    return db_documento


def create_evidencia_viaje(
    db: Session,
    db_viaje: Viaje,
    evidencia_in: ViajeEvidenciaCreate,
) -> Evidencia:
    if not tipo_evidencia_exists(db, evidencia_in.id_tipo_evidencia):
        raise ValueError("El tipo de evidencia especificado no existe")

    if not archivo_storage_exists(db, evidencia_in.id_archivo):
        raise ValueError("El archivo especificado no existe")

    if evidencia_in.id_operador is not None and not operador_exists(db, evidencia_in.id_operador):
        raise ValueError("El operador especificado no existe")

    evidencia_data = {
        "id_viaje": db_viaje.id_viaje,
        "id_evento_operativo": evidencia_in.id_evento_operativo,
        "id_tipo_evidencia": evidencia_in.id_tipo_evidencia,
        "id_operador": evidencia_in.id_operador,
        "id_archivo": evidencia_in.id_archivo,
        "comentario": evidencia_in.comentario,
        "latitud": evidencia_in.latitud,
        "longitud": evidencia_in.longitud,
    }

    if evidencia_in.fecha_captura is not None:
        evidencia_data["fecha_captura"] = evidencia_in.fecha_captura

    db_evidencia = Evidencia(
        **evidencia_data,
    )
    db.add(db_evidencia)
    db.commit()
    db.refresh(db_evidencia)
    return db_evidencia


def _crear_evidencias_operativas_para_evento(
    db: Session,
    db_viaje: Viaje,
    db_evento: EventoOperativoViaje,
    evidencias: list[EvidenciaOperativaInput],
) -> list[Evidencia]:
    evidencias_creadas: list[Evidencia] = []

    for evidencia_in in evidencias:
        if not tipo_evidencia_exists(db, evidencia_in.id_tipo_evidencia):
            raise ValueError("El tipo de evidencia especificado no existe")

        if not archivo_storage_exists(db, evidencia_in.id_archivo):
            raise ValueError("El archivo especificado no existe")

        db_evidencia = Evidencia(
            id_viaje=db_viaje.id_viaje,
            id_evento_operativo=db_evento.id_evento,
            id_tipo_evidencia=evidencia_in.id_tipo_evidencia,
            id_operador=db_viaje.id_operador_actual,
            id_archivo=evidencia_in.id_archivo,
            comentario=evidencia_in.comentario,
            latitud=evidencia_in.latitud,
            longitud=evidencia_in.longitud,
        )
        db.add(db_evidencia)
        evidencias_creadas.append(db_evidencia)

    return evidencias_creadas


def update_evidencia_viaje(
    db: Session,
    db_evidencia: Evidencia,
    evidencia_in: ViajeEvidenciaUpdate,
) -> Evidencia:
    update_data = evidencia_in.model_dump(exclude_unset=True)

    if "id_tipo_evidencia" in update_data and update_data["id_tipo_evidencia"] is None:
        raise ValueError("El tipo de evidencia no puede ser nulo")

    if "id_archivo" in update_data and update_data["id_archivo"] is None:
        raise ValueError("El archivo de la evidencia no puede ser nulo")

    if "fecha_captura" in update_data and update_data["fecha_captura"] is None:
        raise ValueError("La fecha de captura no puede ser nula")

    if "id_tipo_evidencia" in update_data and not tipo_evidencia_exists(db, update_data["id_tipo_evidencia"]):
        raise ValueError("El tipo de evidencia especificado no existe")

    if "id_archivo" in update_data and not archivo_storage_exists(db, update_data["id_archivo"]):
        raise ValueError("El archivo especificado no existe")

    if (
        "id_operador" in update_data
        and update_data["id_operador"] is not None
        and not operador_exists(db, update_data["id_operador"])
    ):
        raise ValueError("El operador especificado no existe")

    for field, value in update_data.items():
        setattr(db_evidencia, field, value)

    db.commit()
    db.refresh(db_evidencia)
    return db_evidencia


def delete_evidencia_viaje(db: Session, db_evidencia: Evidencia) -> None:
    db.delete(db_evidencia)
    db.commit()


def get_asignacion_activa_by_viaje(db: Session, viaje_id: int) -> AsignacionViaje | None:
    return (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_viaje == viaje_id,
            AsignacionViaje.activo.is_(True),
        )
        .first()
    )


def get_asignaciones_by_viaje(db: Session, viaje_id: int) -> list[AsignacionViaje]:
    return (
        db.query(AsignacionViaje)
        .filter(AsignacionViaje.id_viaje == viaje_id)
        .order_by(AsignacionViaje.id_asignacion.desc())
        .all()
    )


def get_asignaciones_enriched_by_viaje(db: Session, viaje_id: int) -> list[AsignacionViaje]:
    return (
        db.query(AsignacionViaje)
        .options(
            joinedload(AsignacionViaje.operador),
            joinedload(AsignacionViaje.trailer),
            joinedload(AsignacionViaje.caja),
            joinedload(AsignacionViaje.usuario_creador),
        )
        .filter(AsignacionViaje.id_viaje == viaje_id)
        .order_by(AsignacionViaje.id_asignacion.desc())
        .all()
    )


def get_historial_by_viaje(db: Session, viaje_id: int) -> list[HistorialEstatusViaje]:
    return (
        db.query(HistorialEstatusViaje)
        .filter(HistorialEstatusViaje.id_viaje == viaje_id)
        .order_by(HistorialEstatusViaje.id_historial.asc())
        .all()
    )


def get_historial_enriched_by_viaje(db: Session, viaje_id: int) -> list[HistorialEstatusViaje]:
    return (
        db.query(HistorialEstatusViaje)
        .options(
            joinedload(HistorialEstatusViaje.estatus),
            joinedload(HistorialEstatusViaje.usuario_cambio),
        )
        .filter(HistorialEstatusViaje.id_viaje == viaje_id)
        .order_by(HistorialEstatusViaje.id_historial.asc())
        .all()
    )


def get_eventos_operativos_by_viaje(db: Session, viaje_id: int) -> list[EventoOperativoViaje]:
    return (
        db.query(EventoOperativoViaje)
        .options(
            joinedload(EventoOperativoViaje.operador),
            joinedload(EventoOperativoViaje.trailer),
            joinedload(EventoOperativoViaje.caja),
            selectinload(EventoOperativoViaje.evidencias).joinedload(Evidencia.archivo),
        )
        .filter(EventoOperativoViaje.id_viaje == viaje_id)
        .order_by(EventoOperativoViaje.created_at.desc(), EventoOperativoViaje.id_evento.desc())
        .all()
    )


def get_evento_operativo_by_id_and_viaje(
    db: Session,
    viaje_id: int,
    evento_id: int,
) -> EventoOperativoViaje | None:
    return (
        db.query(EventoOperativoViaje)
        .filter(
            EventoOperativoViaje.id_viaje == viaje_id,
            EventoOperativoViaje.id_evento == evento_id,
        )
        .first()
    )


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

    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
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


def _crear_evento_operativo_viaje(
    db: Session,
    db_viaje: Viaje,
    tipo_evento: TipoEventoOperativo,
    payload: EventoOperativoCargaPayload | EventoOperativoRetrasoPayload | EventoOperativoViajePayload,
    changed_by: int | None = None,
) -> EventoOperativoViaje:
    _validar_payload_operativo_por_accion(db, db_viaje, tipo_evento, payload)

    db_evento = EventoOperativoViaje(
        id_viaje=db_viaje.id_viaje,
        id_operador=db_viaje.id_operador_actual,
        id_trailer=db_viaje.id_trailer_actual,
        id_caja=db_viaje.id_caja_actual,
        tipo_evento=tipo_evento,
        kilometraje=getattr(payload, "kilometraje", None),
        nivel_diesel=getattr(payload, "nivel_diesel", None),
        ubicacion=payload.ubicacion.strip(),
        latitud=payload.latitud,
        longitud=payload.longitud,
        comentario=payload.comentario,
        created_by=changed_by,
    )
    db.add(db_evento)
    return db_evento


def _crear_evento_y_evidencias_operativas(
    db: Session,
    db_viaje: Viaje,
    tipo_evento: TipoEventoOperativo,
    payload: EventoOperativoCargaPayload | EventoOperativoRetrasoPayload | EventoOperativoViajePayload,
    changed_by: int | None = None,
) -> EventoOperativoViaje:
    db_evento = _crear_evento_operativo_viaje(
        db,
        db_viaje,
        tipo_evento,
        payload,
        changed_by=changed_by,
    )
    db.flush()

    if payload.evidencias:
        _crear_evidencias_operativas_para_evento(
            db,
            db_viaje,
            db_evento,
            payload.evidencias,
        )
        db.flush()

    return db_evento


def update_evento_operativo_viaje(
    db: Session,
    db_evento: EventoOperativoViaje,
    evento_in: EventoOperativoViajeUpdatePayload,
) -> EventoOperativoViaje:
    update_data = evento_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_evento, field, value)

    db.commit()
    db.refresh(db_evento)
    return db_evento


def es_estatus_terminal(db: Session, estatus_id: int) -> bool:
    estatus = get_estatus_by_id(db, estatus_id)
    return bool(estatus and estatus.es_terminal)


def viaje_esta_terminal(db_viaje: Viaje) -> bool:
    estatus_actual = db_viaje.estatus_actual
    return bool(estatus_actual and estatus_actual.es_terminal)


def validar_viaje_no_terminal_para_mutacion(db_viaje: Viaje) -> None:
    if viaje_esta_terminal(db_viaje):
        raise ValueError(
            f"El viaje ya está {db_viaje.estatus_actual.clave} y no admite nuevas acciones operativas."
        )


def transicion_permitida(
    db: Session,
    estatus_origen_id: int,
    estatus_destino_id: int,
) -> TransicionEstatusViaje | None:
    return (
        db.query(TransicionEstatusViaje)
        .filter(
            TransicionEstatusViaje.id_estatus_origen == estatus_origen_id,
            TransicionEstatusViaje.id_estatus_destino == estatus_destino_id,
            TransicionEstatusViaje.activo.is_(True),
        )
        .first()
    )


def _viaje_tiene_evidencias_validas(db: Session, viaje_id: int) -> bool:
    return (
        db.query(Evidencia.id_evidencia)
        .join(ArchivoStorage, Evidencia.id_archivo == ArchivoStorage.id_archivo)
        .filter(
            Evidencia.id_viaje == viaje_id,
            Evidencia.id_archivo.isnot(None),
        )
        .first()
        is not None
    )


def _payload_tiene_evidencias_validas(
    db: Session,
    evidencias_en_payload: list[EvidenciaOperativaInput] | None,
) -> bool:
    if not evidencias_en_payload:
        return False

    evidencia_valida = False
    for evidencia_in in evidencias_en_payload:
        if not tipo_evidencia_exists(db, evidencia_in.id_tipo_evidencia):
            raise ValueError("El tipo de evidencia especificado no existe")

        if not archivo_storage_exists(db, evidencia_in.id_archivo):
            raise ValueError("El archivo especificado no existe")

        evidencia_valida = True

    return evidencia_valida


def _validar_requisitos_evidencia_transicion(
    db: Session,
    db_viaje: Viaje,
    transicion: TransicionEstatusViaje,
    estatus_destino: CatalogoEstatusViaje,
    evidencias_en_payload: list[EvidenciaOperativaInput] | None = None,
) -> None:
    if not transicion.requiere_evidencia:
        return

    tiene_evidencias_validas = _viaje_tiene_evidencias_validas(db, db_viaje.id_viaje) or _payload_tiene_evidencias_validas(
        db,
        evidencias_en_payload,
    )

    if estatus_destino.clave == "INICIADO":
        if not tiene_evidencias_validas:
            raise ValueError(
                "La transición a INICIADO requiere al menos una evidencia asociada al viaje con id_archivo válido"
            )
    elif estatus_destino.clave == "FINALIZADO":
        if not tiene_evidencias_validas:
            raise ValueError(
                "La transición a FINALIZADO requiere al menos una evidencia asociada al viaje con id_archivo válido"
            )
        # Punto de extensión: aquí podrá diferenciarse evidencia de cierre por tipo.
    elif not tiene_evidencias_validas:
        raise ValueError(
            f"La transición a {estatus_destino.clave} requiere al menos una evidencia asociada al viaje con id_archivo válido"
        )

    if settings.strict_evidence_validation:
        _validar_documentos_transicion_strict(db, db_viaje, estatus_destino)


def _validar_documentos_transicion_strict(
    db: Session,
    db_viaje: Viaje,
    estatus_destino: CatalogoEstatusViaje,
) -> None:
    entidades = _obtener_entidades_documentales_viaje(db_viaje)
    requisitos = _obtener_requisitos_documentales_por_estatus(estatus_destino.clave, entidades)

    for requisito in requisitos:
        _validar_requisito_documental(db, requisito, entidades, estatus_destino.clave)


def _obtener_entidades_documentales_viaje(db_viaje: Viaje) -> dict[str, object | None]:
    return {
        "VIAJE": db_viaje,
        "OPERADOR": db_viaje.operador_actual,
        "TRAILER": db_viaje.trailer_actual,
        "CAJA": db_viaje.caja_actual,
    }


def _obtener_requisitos_documentales_por_estatus(
    clave_estatus_destino: str,
    entidades: dict[str, object | None],
) -> list[dict[str, object]]:
    if clave_estatus_destino == "INICIADO":
        requisitos = [
            {"aplica_a": "OPERADOR", "obligatorio": True},
            {"aplica_a": "TRAILER", "obligatorio": True},
        ]
        if entidades.get("CAJA") is not None:
            requisitos.append({"aplica_a": "CAJA", "obligatorio": True})
        return requisitos

    if clave_estatus_destino == "FINALIZADO":
        requisitos = []
        if entidades.get("OPERADOR") is not None:
            requisitos.append({"aplica_a": "OPERADOR", "obligatorio": False})
        if entidades.get("TRAILER") is not None:
            requisitos.append({"aplica_a": "TRAILER", "obligatorio": False})
        if entidades.get("CAJA") is not None:
            requisitos.append({"aplica_a": "CAJA", "obligatorio": False})
        return requisitos

    return []


def _obtener_documentos_por_entidad(
    db: Session,
    aplica_a: str,
    entidad_id: int,
) -> list[Documento]:
    query = db.query(Documento).options(joinedload(Documento.tipo_documento))

    if aplica_a == "VIAJE":
        query = query.filter(Documento.id_viaje == entidad_id)
    elif aplica_a == "OPERADOR":
        query = query.filter(Documento.id_operador == entidad_id)
    elif aplica_a == "TRAILER":
        query = query.filter(Documento.id_trailer == entidad_id)
    elif aplica_a == "CAJA":
        query = query.filter(Documento.id_caja == entidad_id)
    else:
        return []

    return query.all()


def _documento_esta_vigente(documento: Documento, hoy: date | None = None) -> bool:
    if not documento.activo:
        return False

    if documento.estatus != "VIGENTE":
        return False

    tipo_documento = documento.tipo_documento
    if not tipo_documento or not tipo_documento.requiere_vigencia:
        return True

    fecha_referencia = hoy or date.today()
    if documento.fecha_expiracion is None:
        return False

    return documento.fecha_expiracion >= fecha_referencia


def _validar_requisito_documental(
    db: Session,
    requisito: dict[str, object],
    entidades: dict[str, object | None],
    clave_estatus_destino: str,
) -> None:
    aplica_a = str(requisito["aplica_a"])
    obligatorio = bool(requisito.get("obligatorio", True))
    entidad = entidades.get(aplica_a)
    nombre_entidad = _formatear_nombre_entidad_documental(aplica_a)

    if entidad is None:
        if obligatorio:
            raise ValueError(
                f"La transición a {clave_estatus_destino} requiere {nombre_entidad} para validar documentos"
            )
        return

    entidad_id = getattr(entidad, f"id_{aplica_a.lower()}", None)
    if entidad_id is None and aplica_a == "VIAJE":
        entidad_id = getattr(entidad, "id_viaje", None)

    if entidad_id is None:
        if obligatorio:
            raise ValueError(
                f"La transición a {clave_estatus_destino} requiere {nombre_entidad} válido para validar documentos"
            )
        return

    documentos = _obtener_documentos_por_entidad(db, aplica_a, entidad_id)
    if not documentos:
        if obligatorio:
            raise ValueError(
                f"La transición a {clave_estatus_destino} requiere al menos un documento vigente de {nombre_entidad}"
            )
        return

    documentos_vigentes = [documento for documento in documentos if _documento_esta_vigente(documento)]
    if not documentos_vigentes:
        raise ValueError(
            f"{nombre_entidad.capitalize()} no tiene documentos vigentes para permitir la transición a {clave_estatus_destino}"
        )


def _formatear_nombre_entidad_documental(aplica_a: str) -> str:
    nombres = {
        "VIAJE": "el viaje",
        "OPERADOR": "el operador actual",
        "TRAILER": "el tráiler actual",
        "CAJA": "la caja actual",
    }
    return nombres.get(aplica_a, "la entidad requerida")


def get_operadores_disponibles(db: Session) -> list[Operador]:
    subquery_operadores_ocupados = (
        db.query(AsignacionViaje.id_operador)
        .filter(
            AsignacionViaje.activo.is_(True),
            AsignacionViaje.id_operador.isnot(None),
        )
        .subquery()
    )

    return (
        db.query(Operador)
        .filter(
            Operador.activo.is_(True),
            ~Operador.id_operador.in_(subquery_operadores_ocupados),
        )
        .all()
    )


def get_trailers_disponibles(db: Session) -> list[Trailer]:
    subquery_trailers_ocupados = (
        db.query(AsignacionViaje.id_trailer)
        .filter(
            AsignacionViaje.activo.is_(True),
            AsignacionViaje.id_trailer.isnot(None),
        )
        .subquery()
    )

    trailers = (
        db.query(Trailer)
        .filter(
            Trailer.activo.is_(True),
            ~Trailer.id_trailer.in_(subquery_trailers_ocupados),
        )
        .all()
    )
    mantenimientos = get_mantenimientos_activos_por_tipo(db, "TRAILER")
    return [trailer for trailer in trailers if trailer.id_trailer not in mantenimientos]


def get_cajas_disponibles(db: Session) -> list[Caja]:
    subquery_cajas_asignadas = (
        db.query(AsignacionViaje.id_caja)
        .filter(
            AsignacionViaje.activo.is_(True),
            AsignacionViaje.id_caja.isnot(None),
        )
        .subquery()
    )

    subquery_cajas_en_viajes_activos = (
        db.query(Viaje.id_caja_actual)
        .join(CatalogoEstatusViaje, Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus)
        .filter(
            Viaje.id_caja_actual.isnot(None),
            CatalogoEstatusViaje.es_terminal.is_(False),
        )
        .subquery()
    )

    cajas = (
        db.query(Caja)
        .filter(
            Caja.activo.is_(True),
            ~Caja.id_caja.in_(subquery_cajas_asignadas),
            ~Caja.id_caja.in_(subquery_cajas_en_viajes_activos),
        )
        .all()
    )
    mantenimientos = get_mantenimientos_activos_por_tipo(db, "CAJA")
    return [caja for caja in cajas if caja.id_caja not in mantenimientos]


def _build_viaje_actual_resumen(db_viaje: Viaje | None) -> dict[str, object] | None:
    if not db_viaje:
        return None

    return {
        "id_viaje": db_viaje.id_viaje,
        "folio": db_viaje.folio,
        "estatus_clave": db_viaje.estatus_actual.clave if db_viaje.estatus_actual else None,
    }


def get_disponibilidad_resumen(db: Session) -> dict[str, list[dict[str, object]]]:
    viajes_no_terminales = (
        db.query(Viaje)
        .options(joinedload(Viaje.estatus_actual))
        .join(CatalogoEstatusViaje, Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus)
        .filter(CatalogoEstatusViaje.es_terminal.is_(False))
        .all()
    )

    viajes_por_operador = {
        viaje.id_operador_actual: viaje
        for viaje in viajes_no_terminales
        if viaje.id_operador_actual is not None
    }
    viajes_por_trailer = {
        viaje.id_trailer_actual: viaje
        for viaje in viajes_no_terminales
        if viaje.id_trailer_actual is not None
    }
    viajes_por_caja = {
        viaje.id_caja_actual: viaje
        for viaje in viajes_no_terminales
        if viaje.id_caja_actual is not None
    }
    mantenimientos_trailer = get_mantenimientos_activos_por_tipo(db, "TRAILER")
    mantenimientos_caja = get_mantenimientos_activos_por_tipo(db, "CAJA")

    operadores = (
        db.query(Operador)
        .options(joinedload(Operador.usuario))
        .order_by(Operador.alias.asc(), Operador.id_operador.asc())
        .all()
    )
    trailers = (
        db.query(Trailer)
        .order_by(Trailer.numero_economico.asc(), Trailer.id_trailer.asc())
        .all()
    )
    cajas = (
        db.query(Caja)
        .order_by(Caja.numero_economico.asc().nullslast(), Caja.placas.asc(), Caja.id_caja.asc())
        .all()
    )

    operadores_resumen: list[dict[str, object]] = []
    for operador in operadores:
        viaje_actual = viajes_por_operador.get(operador.id_operador)
        disponible = bool(operador.activo and viaje_actual is None)
        motivo = None
        if not operador.activo:
            motivo = "Registro inactivo"
        elif viaje_actual is not None:
            motivo = f"Asignado al viaje {viaje_actual.folio}"

        nombre_completo = None
        if operador.usuario is not None:
            nombre_completo = f"{operador.usuario.nombre} {operador.usuario.apellido}".strip()

        operadores_resumen.append(
            {
                "id_operador": operador.id_operador,
                "alias": operador.alias,
                "username": operador.usuario.username if operador.usuario is not None else None,
                "nombre_completo": nombre_completo,
                "numero_licencia": operador.numero_licencia,
                "activo": operador.activo,
                "disponible": disponible,
                "viaje_actual": _build_viaje_actual_resumen(viaje_actual),
                "motivo_no_disponible": motivo,
            }
        )

    trailers_resumen: list[dict[str, object]] = []
    for trailer in trailers:
        viaje_actual = viajes_por_trailer.get(trailer.id_trailer)
        mantenimiento = mantenimientos_trailer.get(trailer.id_trailer)
        disponible = bool(trailer.activo and viaje_actual is None and mantenimiento is None)
        motivo = None
        if not trailer.activo:
            motivo = "Registro inactivo"
        elif mantenimiento is not None:
            motivo = "En mantenimiento"
        elif viaje_actual is not None:
            motivo = f"Asignado al viaje {viaje_actual.folio}"

        trailers_resumen.append(
            {
                "id_trailer": trailer.id_trailer,
                "numero_economico": trailer.numero_economico,
                "placas": trailer.placas,
                "marca": trailer.marca,
                "modelo": trailer.modelo,
                "numero_serie": trailer.numero_serie,
                "activo": trailer.activo,
                "disponible": disponible,
                "viaje_actual": _build_viaje_actual_resumen(viaje_actual),
                "motivo_no_disponible": motivo,
            }
        )

    cajas_resumen: list[dict[str, object]] = []
    for caja in cajas:
        viaje_actual = viajes_por_caja.get(caja.id_caja)
        mantenimiento = mantenimientos_caja.get(caja.id_caja)
        disponible = bool(caja.activo and viaje_actual is None and mantenimiento is None)
        motivo = None
        if not caja.activo:
            motivo = "Registro inactivo"
        elif mantenimiento is not None:
            motivo = "En mantenimiento"
        elif viaje_actual is not None:
            motivo = f"Ligada al viaje {viaje_actual.folio}"

        cajas_resumen.append(
            {
                "id_caja": caja.id_caja,
                "numero_economico": caja.numero_economico,
                "placas": caja.placas,
                "tipo_caja": caja.tipo_caja,
                "modelo": caja.modelo,
                "numero_serie": caja.numero_serie,
                "activo": caja.activo,
                "disponible": disponible,
                "viaje_actual": _build_viaje_actual_resumen(viaje_actual),
                "motivo_no_disponible": motivo,
            }
        )

    return {
        "operadores": operadores_resumen,
        "trailers": trailers_resumen,
        "cajas": cajas_resumen,
    }


def operador_disponible_para_asignacion(
    db: Session,
    operador_id: int,
    viaje_id: int | None = None,
) -> bool:
    asignacion = (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_operador == operador_id,
            AsignacionViaje.activo.is_(True),
        )
        .first()
    )

    if not asignacion:
        return True

    return viaje_id is not None and asignacion.id_viaje == viaje_id


def trailer_disponible_para_asignacion(
    db: Session,
    trailer_id: int,
    viaje_id: int | None = None,
) -> bool:
    if trailer_en_mantenimiento(db, trailer_id):
        return False

    asignacion = (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_trailer == trailer_id,
            AsignacionViaje.activo.is_(True),
        )
        .first()
    )

    if not asignacion:
        return True

    return viaje_id is not None and asignacion.id_viaje == viaje_id


def caja_disponible_para_asignacion(
    db: Session,
    caja_id: int,
    viaje_id: int | None = None,
) -> bool:
    if caja_en_mantenimiento(db, caja_id):
        return False

    asignacion_activa = (
        db.query(AsignacionViaje)
        .filter(
            AsignacionViaje.id_caja == caja_id,
            AsignacionViaje.activo.is_(True),
        )
        .first()
    )
    if asignacion_activa and not (viaje_id is not None and asignacion_activa.id_viaje == viaje_id):
        return False

    viaje_activo = (
        db.query(Viaje)
        .join(CatalogoEstatusViaje, Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus)
        .filter(
            Viaje.id_caja_actual == caja_id,
            CatalogoEstatusViaje.es_terminal.is_(False),
        )
        .first()
    )

    if not viaje_activo:
        return True

    return viaje_id is not None and viaje_activo.id_viaje == viaje_id


def create_viaje(db: Session, viaje_in: ViajeCreate, created_by: int | None = None) -> Viaje:
    estatus_creado = get_estatus_by_clave(db, "CREADO")
    if not estatus_creado:
        raise ValueError("No existe el estatus base CREADO")

    db_viaje = Viaje(
        folio=viaje_in.folio,
        folio_viaje_cliente=viaje_in.folio_viaje_cliente,
        id_cliente=viaje_in.id_cliente,
        lugar_inicio=viaje_in.lugar_inicio,
        lugar_destino=viaje_in.lugar_destino,
        lugar_inicio_latitud=viaje_in.lugar_inicio_latitud,
        lugar_inicio_longitud=viaje_in.lugar_inicio_longitud,
        lugar_destino_latitud=viaje_in.lugar_destino_latitud,
        lugar_destino_longitud=viaje_in.lugar_destino_longitud,
        tipo_carga=viaje_in.tipo_carga,
        descripcion_carga=viaje_in.descripcion_carga,
        fecha_programada_salida=viaje_in.fecha_programada_salida,
        fecha_carga=viaje_in.fecha_carga,
        hora_carga=viaje_in.hora_carga,
        fecha_descarga=viaje_in.fecha_descarga,
        hora_descarga=viaje_in.hora_descarga,
        hora_cita_descarga=viaje_in.hora_cita_descarga,
        observaciones=viaje_in.observaciones,
        id_estatus_actual=estatus_creado.id_estatus,
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(db_viaje)
    db.flush()

    historial = HistorialEstatusViaje(
        id_viaje=db_viaje.id_viaje,
        id_estatus=estatus_creado.id_estatus,
        comentario="Viaje creado",
        changed_by=created_by,
    )
    db.add(historial)
    alerta_viaje_creado = crear_alerta_viaje_creado(db, db_viaje)

    db.commit()
    db.refresh(db_viaje)
    notificar_alerta_inmediata_si_aplica(db, alerta_viaje_creado)
    return db_viaje


def update_viaje(db: Session, db_viaje: Viaje, viaje_in: ViajeUpdate) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    update_data = viaje_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_viaje, field, value)

    db.commit()
    db.refresh(db_viaje)
    return db_viaje


def create_asignacion_viaje(
    db: Session,
    db_viaje: Viaje,
    asignacion_in: ViajeAsignacionCreate,
) -> AsignacionViaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    estatus_asignado = get_estatus_by_clave(db, "ASIGNADO")
    if not estatus_asignado:
        raise ValueError("No existe el estatus base ASIGNADO")
    estatus_anterior = get_estatus_by_id(db, db_viaje.id_estatus_actual)

    if not operador_disponible_para_asignacion(db, asignacion_in.id_operador, db_viaje.id_viaje):
        raise ValueError("El operador no está disponible")

    if not trailer_disponible_para_asignacion(db, asignacion_in.id_trailer, db_viaje.id_viaje):
        if trailer_en_mantenimiento(db, asignacion_in.id_trailer):
            raise ValueError("El tráiler está en mantenimiento y no puede asignarse")
        raise ValueError("El tráiler no está disponible")

    if asignacion_in.id_caja is not None and not caja_disponible_para_asignacion(
        db, asignacion_in.id_caja, db_viaje.id_viaje
    ):
        if caja_en_mantenimiento(db, asignacion_in.id_caja):
            raise ValueError("La caja está en mantenimiento y no puede asignarse")
        raise ValueError("La caja no está disponible")

    asignacion_activa = get_asignacion_activa_by_viaje(db, db_viaje.id_viaje)
    if asignacion_activa:
        asignacion_activa.activo = False
        asignacion_activa.fecha_fin_asignacion = datetime.utcnow()

    nueva_asignacion = AsignacionViaje(
        id_viaje=db_viaje.id_viaje,
        id_operador=asignacion_in.id_operador,
        id_trailer=asignacion_in.id_trailer,
        id_caja=asignacion_in.id_caja,
        activo=True,
        motivo=asignacion_in.motivo,
        comentario=asignacion_in.comentario,
        created_by=asignacion_in.created_by,
    )
    db.add(nueva_asignacion)
    db.flush()

    db_viaje.id_operador_actual = asignacion_in.id_operador
    db_viaje.id_trailer_actual = asignacion_in.id_trailer
    db_viaje.id_caja_actual = asignacion_in.id_caja
    db_viaje.id_estatus_actual = estatus_asignado.id_estatus
    db_viaje.updated_by = asignacion_in.created_by

    historial = HistorialEstatusViaje(
        id_viaje=db_viaje.id_viaje,
        id_estatus=estatus_asignado.id_estatus,
        comentario=asignacion_in.comentario or "Viaje asignado",
        changed_by=asignacion_in.created_by,
    )
    db.add(historial)
    alerta_asignacion = crear_alerta_asignacion_viaje(
        db,
        db_viaje,
        _get_operador_display_name(db, asignacion_in.id_operador),
    )
    alerta_cambio_estatus = None
    if not estatus_anterior or estatus_anterior.clave != estatus_asignado.clave:
        alerta_cambio_estatus = crear_alerta_cambio_estatus_viaje(
            db,
            db_viaje,
            estatus_anterior.clave if estatus_anterior else "SIN_ESTATUS",
            estatus_asignado.clave,
        )

    db.commit()
    db.refresh(nueva_asignacion)
    notificar_alerta_inmediata_si_aplica(db, alerta_asignacion)
    notificar_alerta_inmediata_si_aplica(db, alerta_cambio_estatus)
    return nueva_asignacion


def cambiar_estatus_viaje(
    db: Session,
    db_viaje: Viaje,
    cambio_in: ViajeCambioEstatus,
    evidencias_en_payload: list[EvidenciaOperativaInput] | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
    estatus_destino = get_estatus_by_id(db, cambio_in.id_estatus_destino)

    if not estatus_actual or not estatus_destino:
        raise ValueError("Estatus actual o destino inválido")

    transicion = transicion_permitida(
        db,
        db_viaje.id_estatus_actual,
        cambio_in.id_estatus_destino,
    )
    if not transicion:
        raise ValueError("La transición de estatus no está permitida")

    if transicion.requiere_comentario and not cambio_in.comentario:
        raise ValueError("Esta transición requiere comentario")

    _validar_requisitos_evidencia_transicion(
        db,
        db_viaje,
        transicion,
        estatus_destino,
        evidencias_en_payload=evidencias_en_payload,
    )

    asignacion_activa = get_asignacion_activa_by_viaje(db, db_viaje.id_viaje)

    if estatus_destino.clave in {"ASIGNADO", "CARGANDO", "INICIADO"} and not asignacion_activa:
        raise ValueError("El viaje requiere una asignación activa para este estatus")

    if estatus_destino.clave == "INICIADO":
        if db_viaje.fecha_inicio is None:
            db_viaje.fecha_inicio = datetime.utcnow()
        if asignacion_activa and asignacion_activa.fecha_inicio_operacion is None:
            asignacion_activa.fecha_inicio_operacion = datetime.utcnow()

    if estatus_destino.clave == "STANDBY":
        if asignacion_activa:
            asignacion_activa.activo = False
            asignacion_activa.fecha_fin_asignacion = datetime.utcnow()

        db_viaje.id_operador_actual = None
        db_viaje.id_trailer_actual = None
        # La caja se mantiene asociada al viaje.

    if estatus_destino.clave in {"FINALIZADO", "CANCELADO"}:
        if asignacion_activa:
            asignacion_activa.activo = False
            asignacion_activa.fecha_fin_asignacion = datetime.utcnow()

        db_viaje.id_operador_actual = None
        db_viaje.id_trailer_actual = None
        db_viaje.id_caja_actual = None

        if estatus_destino.clave == "FINALIZADO" and db_viaje.fecha_llegada is None:
            db_viaje.fecha_llegada = datetime.utcnow()

    db_viaje.id_estatus_actual = estatus_destino.id_estatus
    db_viaje.updated_by = cambio_in.changed_by

    historial = HistorialEstatusViaje(
        id_viaje=db_viaje.id_viaje,
        id_estatus=estatus_destino.id_estatus,
        comentario=cambio_in.comentario,
        changed_by=cambio_in.changed_by,
    )
    db.add(historial)
    alerta_cambio_estatus = crear_alerta_cambio_estatus_viaje(
        db,
        db_viaje,
        estatus_actual.clave,
        estatus_destino.clave,
    )

    db.commit()
    db.refresh(db_viaje)
    notificar_alerta_inmediata_si_aplica(db, alerta_cambio_estatus)
    return db_viaje
def get_transiciones_disponibles_by_viaje(
    db: Session,
    db_viaje: Viaje,
) -> list[TransicionEstatusViaje]:
    return (
        db.query(TransicionEstatusViaje)
        .filter(
            TransicionEstatusViaje.id_estatus_origen == db_viaje.id_estatus_actual,
            TransicionEstatusViaje.activo.is_(True),
        )
        .all()
    )


def cambiar_estatus_por_clave(
    db: Session,
    db_viaje: Viaje,
    clave_destino: str,
    changed_by: int | None = None,
    comentario: str | None = None,
    evidencias_en_payload: list[EvidenciaOperativaInput] | None = None,
) -> Viaje:
    estatus_destino = get_estatus_by_clave(db, clave_destino)
    if not estatus_destino:
        raise ValueError(f"No existe el estatus destino {clave_destino}")

    cambio = ViajeCambioEstatus(
        id_estatus_destino=estatus_destino.id_estatus,
        changed_by=changed_by,
        comentario=comentario,
    )
    return cambiar_estatus_viaje(
        db,
        db_viaje,
        cambio,
        evidencias_en_payload=evidencias_en_payload,
    )


def iniciar_carga_viaje(
    db: Session,
    db_viaje: Viaje,
    evento_in: EventoOperativoCargaPayload,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
    if not estatus_actual or estatus_actual.clave != "ASIGNADO":
        clave_actual = estatus_actual.clave if estatus_actual else "DESCONOCIDO"
        raise ValueError(
            "Solo se puede iniciar carga cuando el viaje está ASIGNADO. "
            f"Estatus actual: {clave_actual}."
        )

    if _viaje_tiene_evento_operativo(db, db_viaje.id_viaje, "INICIO_CARGA"):
        raise ValueError("El viaje ya registró inicio de carga y no puede repetir esta acción")

    _crear_evento_y_evidencias_operativas(
        db,
        db_viaje,
        "INICIO_CARGA",
        evento_in,
        changed_by=changed_by,
    )
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "CARGANDO",
        changed_by=changed_by,
        comentario=comentario or evento_in.comentario or "Viaje en proceso de carga",
    )


def iniciar_viaje(
    db: Session,
    db_viaje: Viaje,
    evento_in: EventoOperativoViajePayload,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    if _viaje_tiene_evento_operativo(db, db_viaje.id_viaje, "INICIO_VIAJE"):
        raise ValueError("El viaje ya registró inicio de viaje y no puede repetir esta acción")

    _crear_evento_y_evidencias_operativas(
        db,
        db_viaje,
        "INICIO_VIAJE",
        evento_in,
        changed_by=changed_by,
    )
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "INICIADO",
        changed_by=changed_by,
        comentario=comentario or "Viaje iniciado",
        evidencias_en_payload=evento_in.evidencias,
    )


def marcar_retraso_viaje(
    db: Session,
    db_viaje: Viaje,
    evento_in: EventoOperativoRetrasoPayload,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    _crear_evento_y_evidencias_operativas(
        db,
        db_viaje,
        "RETRASO",
        evento_in,
        changed_by=changed_by,
    )
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "RETRASADO",
        changed_by=changed_by,
        comentario=comentario or evento_in.comentario or "Viaje retrasado",
    )


def poner_standby_viaje(
    db: Session,
    db_viaje: Viaje,
    evento_in: EventoOperativoViajePayload,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    _crear_evento_y_evidencias_operativas(
        db,
        db_viaje,
        "STANDBY",
        evento_in,
        changed_by=changed_by,
    )
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "STANDBY",
        changed_by=changed_by,
        comentario=comentario or "Viaje en standby",
    )


def solicitar_standby_viaje(
    db: Session,
    db_viaje: Viaje,
    evento_in: EventoOperativoViajePayload,
    changed_by: int | None = None,
) -> EventoOperativoViaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
    if not estatus_actual or estatus_actual.clave not in {"INICIADO", "RETRASADO"}:
        raise ValueError("Solo se puede solicitar standby cuando el viaje está INICIADO o RETRASADO")

    solicitud_pendiente = get_solicitud_standby_pendiente(db, db_viaje)
    if solicitud_pendiente:
        raise ValueError("Ya existe una solicitud de standby pendiente de autorización administrativa")

    db_evento = _crear_evento_y_evidencias_operativas(
        db,
        db_viaje,
        "STANDBY_SOLICITADO",
        evento_in,
        changed_by=changed_by,
    )
    alerta_standby = crear_alerta_standby_solicitado(
        db,
        db_viaje,
        _get_operador_display_name(db, db_viaje.id_operador_actual),
        evento_in.ubicacion,
        evento_in.comentario,
    )
    db.flush()
    db.commit()
    db.refresh(db_evento)
    notificar_alerta_inmediata_si_aplica(db, alerta_standby)
    return db_evento


def autorizar_standby_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
    if estatus_actual and estatus_actual.clave == "STANDBY":
        raise ValueError("El viaje ya se encuentra en STANDBY")

    solicitud_pendiente = get_solicitud_standby_pendiente(db, db_viaje)
    if not solicitud_pendiente:
        raise ValueError("No existe una solicitud de standby pendiente para este viaje")

    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "STANDBY",
        changed_by=changed_by,
        comentario=comentario or "Standby autorizado por administración",
    )


def _viaje_listo_para_reinicio(db: Session, db_viaje: Viaje) -> bool:
    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
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


def reiniciar_viaje(
    db: Session,
    db_viaje: Viaje,
    evento_in: EventoOperativoViajePayload,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    if not _viaje_listo_para_reinicio(db, db_viaje):
        raise ValueError("El viaje no está listo para reinicio operativo")

    asignacion_activa = get_asignacion_activa_by_viaje(db, db_viaje.id_viaje)
    if not asignacion_activa:
        raise ValueError("El viaje requiere una asignación activa para reiniciarse")

    estatus_iniciado = get_estatus_by_clave(db, "INICIADO")
    if not estatus_iniciado:
        raise ValueError("No existe el estatus INICIADO")

    _crear_evento_y_evidencias_operativas(
        db,
        db_viaje,
        "REINICIO_VIAJE",
        evento_in,
        changed_by=changed_by,
    )

    if db_viaje.fecha_inicio is None:
        db_viaje.fecha_inicio = datetime.utcnow()
    if asignacion_activa.fecha_inicio_operacion is None:
        asignacion_activa.fecha_inicio_operacion = datetime.utcnow()

    db_viaje.id_estatus_actual = estatus_iniciado.id_estatus
    db_viaje.updated_by = changed_by

    historial = HistorialEstatusViaje(
        id_viaje=db_viaje.id_viaje,
        id_estatus=estatus_iniciado.id_estatus,
        comentario=comentario or evento_in.comentario or "Viaje reiniciado tras reasignación administrativa",
        changed_by=changed_by,
    )
    db.add(historial)

    db.commit()
    db.refresh(db_viaje)
    return db_viaje


def finalizar_viaje(
    db: Session,
    db_viaje: Viaje,
    evento_in: EventoOperativoViajePayload,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    _crear_evento_y_evidencias_operativas(
        db,
        db_viaje,
        "FINALIZACION_VIAJE",
        evento_in,
        changed_by=changed_by,
    )
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "FINALIZADO",
        changed_by=changed_by,
        comentario=comentario or "Viaje finalizado",
        evidencias_en_payload=evento_in.evidencias,
    )


def cancelar_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "CANCELADO",
        changed_by=changed_by,
        comentario=comentario or "Viaje cancelado",
    )


def reasignar_viaje(
    db: Session,
    db_viaje: Viaje,
    reasignacion_in: ViajeAsignacionCreate,
) -> AsignacionViaje:
    validar_viaje_no_terminal_para_mutacion(db_viaje)
    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
    if not estatus_actual:
        raise ValueError("El viaje no tiene un estatus actual válido")

    if estatus_actual.clave not in {"CREADO", "ASIGNADO", "STANDBY"}:
        raise ValueError("El viaje no puede ser reasignado en su estatus actual")

    payload_reasignacion = reasignacion_in
    if (
        estatus_actual.clave == "STANDBY"
        and reasignacion_in.id_caja is None
        and db_viaje.id_caja_actual is not None
    ):
        payload_reasignacion = ViajeAsignacionCreate(
            id_operador=reasignacion_in.id_operador,
            id_trailer=reasignacion_in.id_trailer,
            id_caja=db_viaje.id_caja_actual,
            created_by=reasignacion_in.created_by,
            motivo=reasignacion_in.motivo,
            comentario=reasignacion_in.comentario,
        )

    return create_asignacion_viaje(db, db_viaje, payload_reasignacion)
