from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.models import (
    ArchivoStorage,
    AsignacionViaje,
    Caja,
    CatalogoEstatusViaje,
    Cliente,
    Documento,
    Evidencia,
    HistorialEstatusViaje,
    Operador,
    Trailer,
    TipoEvidencia,
    TransicionEstatusViaje,
    Viaje,
)
from app.core.config import settings
from app.schemas.evidencia import ViajeEvidenciaCreate, ViajeEvidenciaUpdate
from app.schemas.viaje import ViajeAsignacionCreate, ViajeCambioEstatus, ViajeCreate, ViajeUpdate


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


def cliente_exists(db: Session, cliente_id: int) -> bool:
    return db.query(Cliente).filter(Cliente.id_cliente == cliente_id).first() is not None


def operador_exists(db: Session, operador_id: int) -> bool:
    return db.query(Operador).filter(Operador.id_operador == operador_id).first() is not None


def trailer_exists(db: Session, trailer_id: int) -> bool:
    return db.query(Trailer).filter(Trailer.id_trailer == trailer_id).first() is not None


def caja_exists(db: Session, caja_id: int) -> bool:
    return db.query(Caja).filter(Caja.id_caja == caja_id).first() is not None


def tipo_evidencia_exists(db: Session, tipo_evidencia_id: int) -> bool:
    return (
        db.query(TipoEvidencia)
        .filter(TipoEvidencia.id_tipo_evidencia == tipo_evidencia_id)
        .first()
        is not None
    )


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


def get_archivos_storage_prueba(db: Session) -> list[ArchivoStorage]:
    return (
        db.query(ArchivoStorage)
        .filter(ArchivoStorage.bucket == "mock-viajes")
        .order_by(ArchivoStorage.id_archivo.asc())
        .all()
    )


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


def get_historial_by_viaje(db: Session, viaje_id: int) -> list[HistorialEstatusViaje]:
    return (
        db.query(HistorialEstatusViaje)
        .filter(HistorialEstatusViaje.id_viaje == viaje_id)
        .order_by(HistorialEstatusViaje.id_historial.asc())
        .all()
    )


def es_estatus_terminal(db: Session, estatus_id: int) -> bool:
    estatus = get_estatus_by_id(db, estatus_id)
    return bool(estatus and estatus.es_terminal)


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


def _validar_requisitos_evidencia_transicion(
    db: Session,
    db_viaje: Viaje,
    transicion: TransicionEstatusViaje,
    estatus_destino: CatalogoEstatusViaje,
) -> None:
    if not transicion.requiere_evidencia:
        return

    evidencias_query = db.query(Evidencia).filter(
        Evidencia.id_viaje == db_viaje.id_viaje,
        Evidencia.id_archivo.isnot(None),
    )

    if estatus_destino.clave == "INICIADO":
        if evidencias_query.first() is None:
            raise ValueError(
                "La transición a INICIADO requiere al menos una evidencia asociada al viaje con id_archivo válido"
            )
    elif estatus_destino.clave == "FINALIZADO":
        evidencia_cierre = evidencias_query.first()
        if evidencia_cierre is None:
            raise ValueError(
                "La transición a FINALIZADO requiere al menos una evidencia asociada al viaje"
            )
        # Punto de extensión: aquí podrá diferenciarse evidencia de cierre por tipo.
    elif evidencias_query.first() is None:
        raise ValueError(
            f"La transición a {estatus_destino.clave} requiere al menos una evidencia asociada al viaje"
        )

    if settings.strict_evidence_validation:
        _validar_documentos_transicion_strict(db, db_viaje, estatus_destino)


def _validar_documentos_transicion_strict(
    db: Session,
    db_viaje: Viaje,
    estatus_destino: CatalogoEstatusViaje,
) -> None:
    documentos_viaje = (
        db.query(Documento)
        .filter(Documento.id_viaje == db_viaje.id_viaje)
        .all()
    )

    if not documentos_viaje:
        # Compatibilidad: dejamos preparado el punto de extensión documental sin
        # bloquear transiciones mientras la carga documental completa aún no exista por API.
        return

    documentos_no_vigentes = [
        documento.id_documento
        for documento in documentos_viaje
        if documento.estatus != "VIGENTE"
    ]

    if documentos_no_vigentes:
        raise ValueError(
            f"La transición a {estatus_destino.clave} encontró documentos no vigentes asociados al viaje"
        )


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

    return (
        db.query(Trailer)
        .filter(
            Trailer.activo.is_(True),
            ~Trailer.id_trailer.in_(subquery_trailers_ocupados),
        )
        .all()
    )


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

    return (
        db.query(Caja)
        .filter(
            Caja.activo.is_(True),
            ~Caja.id_caja.in_(subquery_cajas_asignadas),
            ~Caja.id_caja.in_(subquery_cajas_en_viajes_activos),
        )
        .all()
    )


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
        id_cliente=viaje_in.id_cliente,
        lugar_inicio=viaje_in.lugar_inicio,
        lugar_destino=viaje_in.lugar_destino,
        tipo_carga=viaje_in.tipo_carga,
        descripcion_carga=viaje_in.descripcion_carga,
        fecha_programada_salida=viaje_in.fecha_programada_salida,
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

    db.commit()
    db.refresh(db_viaje)
    return db_viaje


def update_viaje(db: Session, db_viaje: Viaje, viaje_in: ViajeUpdate) -> Viaje:
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
    estatus_asignado = get_estatus_by_clave(db, "ASIGNADO")
    if not estatus_asignado:
        raise ValueError("No existe el estatus base ASIGNADO")

    if not operador_disponible_para_asignacion(db, asignacion_in.id_operador, db_viaje.id_viaje):
        raise ValueError("El operador no está disponible")

    if not trailer_disponible_para_asignacion(db, asignacion_in.id_trailer, db_viaje.id_viaje):
        raise ValueError("El tráiler no está disponible")

    if asignacion_in.id_caja is not None and not caja_disponible_para_asignacion(
        db, asignacion_in.id_caja, db_viaje.id_viaje
    ):
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

    db.commit()
    db.refresh(nueva_asignacion)
    return nueva_asignacion


def cambiar_estatus_viaje(
    db: Session,
    db_viaje: Viaje,
    cambio_in: ViajeCambioEstatus,
) -> Viaje:
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

    db.commit()
    db.refresh(db_viaje)
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
) -> Viaje:
    estatus_destino = get_estatus_by_clave(db, clave_destino)
    if not estatus_destino:
        raise ValueError(f"No existe el estatus destino {clave_destino}")

    cambio = ViajeCambioEstatus(
        id_estatus_destino=estatus_destino.id_estatus,
        changed_by=changed_by,
        comentario=comentario,
    )
    return cambiar_estatus_viaje(db, db_viaje, cambio)


def iniciar_carga_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "CARGANDO",
        changed_by=changed_by,
        comentario=comentario or "Viaje en proceso de carga",
    )


def iniciar_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "INICIADO",
        changed_by=changed_by,
        comentario=comentario or "Viaje iniciado",
    )


def marcar_retraso_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "RETRASADO",
        changed_by=changed_by,
        comentario=comentario or "Viaje retrasado",
    )


def poner_standby_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "STANDBY",
        changed_by=changed_by,
        comentario=comentario or "Viaje en standby",
    )


def finalizar_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
    return cambiar_estatus_por_clave(
        db,
        db_viaje,
        "FINALIZADO",
        changed_by=changed_by,
        comentario=comentario or "Viaje finalizado",
    )


def cancelar_viaje(
    db: Session,
    db_viaje: Viaje,
    changed_by: int | None = None,
    comentario: str | None = None,
) -> Viaje:
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
    estatus_actual = get_estatus_by_id(db, db_viaje.id_estatus_actual)
    if not estatus_actual:
        raise ValueError("El viaje no tiene un estatus actual válido")

    if estatus_actual.clave not in {"STANDBY", "ASIGNADO", "CARGANDO"}:
        raise ValueError("El viaje no puede ser reasignado en su estatus actual")

    return create_asignacion_viaje(db, db_viaje, reasignacion_in)
