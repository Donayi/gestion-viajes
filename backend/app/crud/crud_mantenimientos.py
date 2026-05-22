from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.crud.crud_alertas import crear_alerta_entrada_mantenimiento, notificar_alerta_inmediata_si_aplica
from app.models.models import (
    AsignacionViaje,
    ArchivoStorage,
    Caja,
    CatalogoEstatusViaje,
    Mantenimiento,
    MantenimientoArchivo,
    MantenimientoChecklistEvidencia,
    MantenimientoChecklistItem,
    Trailer,
    Viaje,
)
from app.schemas.mantenimiento import (
    EntidadMantenimientoTipo,
    MantenimientoArchivoCreate,
    MantenimientoArchivoUpdate,
    MantenimientoChecklistEvidenciaCreate,
    MantenimientoChecklistEvidenciaUpdate,
    MantenimientoCreate,
    MantenimientoUpdate,
    MantenimientoChecklistItemUpdate,
)


CHECKLIST_BASES: dict[tuple[str, str], tuple[tuple[str, str | None], ...]] = {
    (
        "TRAILER",
        "PREVENTIVO",
    ): (
        ("Frenos", None),
        ("Llantas", None),
        ("Luces", None),
        ("Motor", None),
        ("Sistema eléctrico", None),
        ("Aceite y fluidos", None),
        ("Suspensión", None),
        ("Dirección", None),
        ("Acoplamiento / quinta rueda", None),
        ("Documentación", None),
    ),
    (
        "TRAILER",
        "CORRECTIVO",
    ): (
        ("Diagnóstico de falla", None),
        ("Refacciones utilizadas", None),
        ("Reparación realizada", None),
        ("Prueba funcional", None),
        ("Validación de seguridad", None),
        ("Limpieza final", None),
        ("Documentación / factura", None),
    ),
    (
        "TRAILER",
        "REPARACION",
    ): (
        ("Diagnóstico de falla", None),
        ("Refacciones utilizadas", None),
        ("Reparación realizada", None),
        ("Prueba funcional", None),
        ("Validación de seguridad", None),
        ("Limpieza final", None),
        ("Documentación / factura", None),
    ),
    (
        "CAJA",
        "PREVENTIVO",
    ): (
        ("Llantas", None),
        ("Luces", None),
        ("Puertas", None),
        ("Piso", None),
        ("Sellos", None),
        ("Estructura", None),
        ("Sistema eléctrico", None),
        ("Limpieza interior", None),
        ("Placas / identificación", None),
        ("Documentación", None),
    ),
    (
        "CAJA",
        "CORRECTIVO",
    ): (
        ("Diagnóstico de daño", None),
        ("Reparación de estructura", None),
        ("Puertas / bisagras / chapas", None),
        ("Piso", None),
        ("Sistema eléctrico", None),
        ("Sellos", None),
        ("Prueba funcional", None),
        ("Evidencia final", None),
        ("Documentación / factura", None),
    ),
    (
        "CAJA",
        "REPARACION",
    ): (
        ("Diagnóstico de daño", None),
        ("Reparación de estructura", None),
        ("Puertas / bisagras / chapas", None),
        ("Piso", None),
        ("Sistema eléctrico", None),
        ("Sellos", None),
        ("Prueba funcional", None),
        ("Evidencia final", None),
        ("Documentación / factura", None),
    ),
}

ESTATUS_MANTENIMIENTO_ACTIVO = {"ABIERTO", "EN_PROCESO"}


def _build_mantenimiento_query(db: Session):
    return db.query(Mantenimiento).options(
        joinedload(Mantenimiento.trailer),
        joinedload(Mantenimiento.caja),
        joinedload(Mantenimiento.checklist_items)
        .joinedload(MantenimientoChecklistItem.evidencias)
        .joinedload(MantenimientoChecklistEvidencia.archivo),
        joinedload(Mantenimiento.archivos).joinedload(MantenimientoArchivo.archivo),
    )


def get_mantenimientos(
    db: Session,
    entidad_tipo: EntidadMantenimientoTipo | None = None,
    estatus: str | None = None,
    created_by: int | None = None,
) -> list[Mantenimiento]:
    query = _build_mantenimiento_query(db)
    if entidad_tipo is not None:
        query = query.filter(Mantenimiento.entidad_tipo == entidad_tipo)
    if estatus is not None:
        query = query.filter(Mantenimiento.estatus == estatus)
    if created_by is not None:
        query = query.filter(Mantenimiento.created_by == created_by)
    return query.order_by(Mantenimiento.fecha_inicio.desc(), Mantenimiento.id_mantenimiento.desc()).all()


def get_mantenimiento_by_id(db: Session, mantenimiento_id: int) -> Mantenimiento | None:
    return _build_mantenimiento_query(db).filter(
        Mantenimiento.id_mantenimiento == mantenimiento_id
    ).first()


def trailer_exists(db: Session, trailer_id: int) -> bool:
    return db.query(Trailer.id_trailer).filter(Trailer.id_trailer == trailer_id).first() is not None


def caja_exists(db: Session, caja_id: int) -> bool:
    return db.query(Caja.id_caja).filter(Caja.id_caja == caja_id).first() is not None


def trailer_activo(db: Session, trailer_id: int) -> bool:
    row = db.query(Trailer.activo).filter(Trailer.id_trailer == trailer_id).first()
    return bool(row[0]) if row is not None else False


def caja_activa(db: Session, caja_id: int) -> bool:
    row = db.query(Caja.activo).filter(Caja.id_caja == caja_id).first()
    return bool(row[0]) if row is not None else False


def _trailer_ligado_a_viaje_no_terminal(db: Session, trailer_id: int) -> bool:
    asignacion_activa = db.query(AsignacionViaje.id_asignacion).filter(
        AsignacionViaje.id_trailer == trailer_id,
        AsignacionViaje.activo.is_(True),
    ).first()
    if asignacion_activa:
        return True

    viaje_actual = db.query(Viaje.id_viaje).join(
        CatalogoEstatusViaje,
        Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus,
    ).filter(
        Viaje.id_trailer_actual == trailer_id,
        CatalogoEstatusViaje.es_terminal.is_(False),
    ).first()
    return viaje_actual is not None


def _caja_ligada_a_viaje_no_terminal(db: Session, caja_id: int) -> bool:
    asignacion_activa = db.query(AsignacionViaje.id_asignacion).filter(
        AsignacionViaje.id_caja == caja_id,
        AsignacionViaje.activo.is_(True),
    ).first()
    if asignacion_activa:
        return True

    viaje_actual = db.query(Viaje.id_viaje).join(
        CatalogoEstatusViaje,
        Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus,
    ).filter(
        Viaje.id_caja_actual == caja_id,
        CatalogoEstatusViaje.es_terminal.is_(False),
    ).first()
    return viaje_actual is not None


def recurso_ligado_a_viaje_no_terminal(
    db: Session,
    entidad_tipo: EntidadMantenimientoTipo,
    entidad_id: int,
) -> bool:
    if entidad_tipo == "TRAILER":
        return _trailer_ligado_a_viaje_no_terminal(db, entidad_id)
    return _caja_ligada_a_viaje_no_terminal(db, entidad_id)


def get_mantenimiento_activo_por_recurso(
    db: Session,
    entidad_tipo: EntidadMantenimientoTipo,
    entidad_id: int,
    exclude_mantenimiento_id: int | None = None,
) -> Mantenimiento | None:
    query = _build_mantenimiento_query(db).filter(
        Mantenimiento.entidad_tipo == entidad_tipo,
        Mantenimiento.estatus.in_(ESTATUS_MANTENIMIENTO_ACTIVO),
    )
    if exclude_mantenimiento_id is not None:
        query = query.filter(Mantenimiento.id_mantenimiento != exclude_mantenimiento_id)
    if entidad_tipo == "TRAILER":
        query = query.filter(Mantenimiento.id_trailer == entidad_id)
    else:
        query = query.filter(Mantenimiento.id_caja == entidad_id)
    return query.order_by(Mantenimiento.fecha_inicio.desc(), Mantenimiento.id_mantenimiento.desc()).first()


def trailer_en_mantenimiento(db: Session, trailer_id: int) -> bool:
    return get_mantenimiento_activo_por_recurso(db, "TRAILER", trailer_id) is not None


def caja_en_mantenimiento(db: Session, caja_id: int) -> bool:
    return get_mantenimiento_activo_por_recurso(db, "CAJA", caja_id) is not None


def get_mantenimientos_activos_por_tipo(
    db: Session,
    entidad_tipo: EntidadMantenimientoTipo,
) -> dict[int, Mantenimiento]:
    rows = _build_mantenimiento_query(db).filter(
        Mantenimiento.entidad_tipo == entidad_tipo,
        Mantenimiento.estatus.in_(ESTATUS_MANTENIMIENTO_ACTIVO),
    ).order_by(Mantenimiento.fecha_inicio.desc(), Mantenimiento.id_mantenimiento.desc()).all()

    result: dict[int, Mantenimiento] = {}
    for mantenimiento in rows:
        entidad_id = mantenimiento.entidad_id
        if entidad_id is not None and entidad_id not in result:
            result[entidad_id] = mantenimiento
    return result


def _get_checklist_base(
    entidad_tipo: EntidadMantenimientoTipo,
    tipo_mantenimiento: str,
) -> tuple[tuple[str, str | None], ...]:
    return CHECKLIST_BASES[(entidad_tipo, tipo_mantenimiento)]


def create_mantenimiento(
    db: Session,
    mantenimiento_in: MantenimientoCreate,
    created_by: int | None = None,
) -> Mantenimiento:
    recurso_activo = (
        trailer_activo(db, mantenimiento_in.entidad_id)
        if mantenimiento_in.entidad_tipo == "TRAILER"
        else caja_activa(db, mantenimiento_in.entidad_id)
    )
    if not recurso_activo:
        raise ValueError("El recurso está inactivo y no puede enviarse a mantenimiento")

    if recurso_ligado_a_viaje_no_terminal(db, mantenimiento_in.entidad_tipo, mantenimiento_in.entidad_id):
        raise ValueError("No se puede enviar el recurso a mantenimiento porque está ligado a un viaje no terminal")

    if get_mantenimiento_activo_por_recurso(
        db, mantenimiento_in.entidad_tipo, mantenimiento_in.entidad_id
    ):
        raise ValueError("El recurso ya tiene un mantenimiento abierto o en proceso")

    data = {
        "entidad_tipo": mantenimiento_in.entidad_tipo,
        "tipo_mantenimiento": mantenimiento_in.tipo_mantenimiento,
        "fecha_mantenimiento": mantenimiento_in.fecha_mantenimiento or datetime.utcnow().date(),
        "fecha_proximo_mantenimiento": mantenimiento_in.fecha_proximo_mantenimiento,
        "kilometraje": mantenimiento_in.kilometraje,
        "descripcion": mantenimiento_in.descripcion.strip(),
        "observaciones": mantenimiento_in.observaciones,
        "created_by": created_by,
        "updated_by": created_by,
    }
    if mantenimiento_in.entidad_tipo == "TRAILER":
        data["id_trailer"] = mantenimiento_in.entidad_id
    else:
        data["id_caja"] = mantenimiento_in.entidad_id

    db_mantenimiento = Mantenimiento(**data)
    db.add(db_mantenimiento)
    db.flush()

    for nombre, descripcion in _get_checklist_base(
        mantenimiento_in.entidad_tipo,
        mantenimiento_in.tipo_mantenimiento,
    ):
        db.add(
            MantenimientoChecklistItem(
                id_mantenimiento=db_mantenimiento.id_mantenimiento,
                nombre=nombre,
                descripcion=descripcion,
                completado=False,
            )
        )

    alerta_mantenimiento = crear_alerta_entrada_mantenimiento(db, db_mantenimiento)
    db.commit()
    notificar_alerta_inmediata_si_aplica(db, alerta_mantenimiento)
    return get_mantenimiento_by_id(db, db_mantenimiento.id_mantenimiento)  # type: ignore[return-value]


def update_mantenimiento(
    db: Session,
    db_mantenimiento: Mantenimiento,
    mantenimiento_in: MantenimientoUpdate,
    updated_by: int | None = None,
) -> Mantenimiento:
    if mantenimiento_in.estatus in {"CERRADO", "CANCELADO"}:
        raise ValueError("Usa las acciones dedicadas para cerrar o cancelar el mantenimiento")
    if db_mantenimiento.estatus in {"CERRADO", "CANCELADO"} and mantenimiento_in.estatus in {"ABIERTO", "EN_PROCESO"}:
        raise ValueError("No se puede reabrir un mantenimiento cerrado o cancelado desde esta operación")

    update_data = mantenimiento_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_mantenimiento, field, value)
    db_mantenimiento.updated_by = updated_by
    db.commit()
    return get_mantenimiento_by_id(db, db_mantenimiento.id_mantenimiento)  # type: ignore[return-value]


def cerrar_mantenimiento(
    db: Session,
    db_mantenimiento: Mantenimiento,
    updated_by: int | None = None,
    observaciones: str | None = None,
) -> Mantenimiento:
    if db_mantenimiento.estatus in {"CERRADO", "CANCELADO"}:
        raise ValueError("El mantenimiento ya está cerrado o cancelado")

    db_mantenimiento.estatus = "CERRADO"
    db_mantenimiento.fecha_fin = datetime.utcnow()
    db_mantenimiento.updated_by = updated_by
    if observaciones:
        db_mantenimiento.observaciones = observaciones
    db.commit()
    return get_mantenimiento_by_id(db, db_mantenimiento.id_mantenimiento)  # type: ignore[return-value]


def cancelar_mantenimiento(
    db: Session,
    db_mantenimiento: Mantenimiento,
    updated_by: int | None = None,
    observaciones: str | None = None,
) -> Mantenimiento:
    if db_mantenimiento.estatus in {"CERRADO", "CANCELADO"}:
        raise ValueError("El mantenimiento ya está cerrado o cancelado")

    db_mantenimiento.estatus = "CANCELADO"
    db_mantenimiento.fecha_fin = datetime.utcnow()
    db_mantenimiento.updated_by = updated_by
    if observaciones:
        db_mantenimiento.observaciones = observaciones
    db.commit()
    return get_mantenimiento_by_id(db, db_mantenimiento.id_mantenimiento)  # type: ignore[return-value]


def update_mantenimiento_checklist_item(
    db: Session,
    db_mantenimiento: Mantenimiento,
    item_id: int,
    item_in: MantenimientoChecklistItemUpdate,
    updated_by: int | None = None,
) -> MantenimientoChecklistItem:
    item = db.query(MantenimientoChecklistItem).filter(
        MantenimientoChecklistItem.id_item == item_id,
        MantenimientoChecklistItem.id_mantenimiento == db_mantenimiento.id_mantenimiento,
    ).first()
    if item is None:
        raise ValueError("El item de checklist no pertenece al mantenimiento especificado")

    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    db_mantenimiento.updated_by = updated_by
    db.commit()
    db.refresh(item)
    return item


def archivo_storage_exists(db: Session, archivo_id: int) -> bool:
    return db.query(ArchivoStorage.id_archivo).filter(ArchivoStorage.id_archivo == archivo_id).first() is not None


def get_mantenimiento_archivos(
    db: Session,
    mantenimiento_id: int,
    solo_activos: bool = False,
) -> list[MantenimientoArchivo]:
    query = db.query(MantenimientoArchivo).options(
        joinedload(MantenimientoArchivo.archivo)
    ).filter(MantenimientoArchivo.id_mantenimiento == mantenimiento_id)
    if solo_activos:
        query = query.filter(MantenimientoArchivo.activo.is_(True))
    return query.order_by(MantenimientoArchivo.created_at.desc()).all()


def get_mantenimiento_archivo_by_id(
    db: Session,
    mantenimiento_id: int,
    mantenimiento_archivo_id: int,
) -> MantenimientoArchivo | None:
    return db.query(MantenimientoArchivo).options(
        joinedload(MantenimientoArchivo.archivo)
    ).filter(
        MantenimientoArchivo.id_mantenimiento == mantenimiento_id,
        MantenimientoArchivo.id_mantenimiento_archivo == mantenimiento_archivo_id,
    ).first()


def create_mantenimiento_archivo(
    db: Session,
    db_mantenimiento: Mantenimiento,
    archivo_in: MantenimientoArchivoCreate,
    created_by: int | None = None,
) -> MantenimientoArchivo:
    db_archivo = MantenimientoArchivo(
        id_mantenimiento=db_mantenimiento.id_mantenimiento,
        id_archivo=archivo_in.id_archivo,
        tipo_archivo=archivo_in.tipo_archivo,
        comentario=archivo_in.comentario,
        activo=True,
        created_by=created_by,
    )
    db.add(db_archivo)
    db.commit()
    return get_mantenimiento_archivo_by_id(
        db, db_mantenimiento.id_mantenimiento, db_archivo.id_mantenimiento_archivo
    )  # type: ignore[return-value]


def update_mantenimiento_archivo(
    db: Session,
    db_mantenimiento_archivo: MantenimientoArchivo,
    archivo_in: MantenimientoArchivoUpdate,
) -> MantenimientoArchivo:
    update_data = archivo_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_mantenimiento_archivo, field, value)
    db.commit()
    db.refresh(db_mantenimiento_archivo)
    return db_mantenimiento_archivo


def soft_delete_mantenimiento_archivo(
    db: Session,
    db_mantenimiento_archivo: MantenimientoArchivo,
) -> MantenimientoArchivo:
    db_mantenimiento_archivo.activo = False
    db.commit()
    db.refresh(db_mantenimiento_archivo)
    return db_mantenimiento_archivo


def get_checklist_item_by_id(
    db: Session,
    mantenimiento_id: int,
    item_id: int,
) -> MantenimientoChecklistItem | None:
    return db.query(MantenimientoChecklistItem).options(
        joinedload(MantenimientoChecklistItem.evidencias).joinedload(MantenimientoChecklistEvidencia.archivo)
    ).filter(
        MantenimientoChecklistItem.id_item == item_id,
        MantenimientoChecklistItem.id_mantenimiento == mantenimiento_id,
    ).first()


def get_checklist_item_evidencias(
    db: Session,
    mantenimiento_id: int,
    item_id: int,
    solo_activos: bool = False,
) -> list[MantenimientoChecklistEvidencia]:
    query = db.query(MantenimientoChecklistEvidencia).options(
        joinedload(MantenimientoChecklistEvidencia.archivo)
    ).join(
        MantenimientoChecklistItem,
        MantenimientoChecklistEvidencia.id_item == MantenimientoChecklistItem.id_item,
    ).filter(
        MantenimientoChecklistItem.id_mantenimiento == mantenimiento_id,
        MantenimientoChecklistEvidencia.id_item == item_id,
    )
    if solo_activos:
        query = query.filter(MantenimientoChecklistEvidencia.activo.is_(True))
    return query.order_by(MantenimientoChecklistEvidencia.created_at.desc()).all()


def get_checklist_item_evidencia_by_id(
    db: Session,
    mantenimiento_id: int,
    item_id: int,
    checklist_evidencia_id: int,
) -> MantenimientoChecklistEvidencia | None:
    return db.query(MantenimientoChecklistEvidencia).options(
        joinedload(MantenimientoChecklistEvidencia.archivo)
    ).join(
        MantenimientoChecklistItem,
        MantenimientoChecklistEvidencia.id_item == MantenimientoChecklistItem.id_item,
    ).filter(
        MantenimientoChecklistItem.id_mantenimiento == mantenimiento_id,
        MantenimientoChecklistEvidencia.id_item == item_id,
        MantenimientoChecklistEvidencia.id_checklist_evidencia == checklist_evidencia_id,
    ).first()


def create_checklist_item_evidencia(
    db: Session,
    db_item: MantenimientoChecklistItem,
    evidencia_in: MantenimientoChecklistEvidenciaCreate,
    created_by: int | None = None,
) -> MantenimientoChecklistEvidencia:
    db_evidencia = MantenimientoChecklistEvidencia(
        id_item=db_item.id_item,
        id_archivo=evidencia_in.id_archivo,
        comentario=evidencia_in.comentario,
        activo=True,
        created_by=created_by,
    )
    db.add(db_evidencia)
    db.commit()
    return get_checklist_item_evidencia_by_id(
        db,
        db_item.id_mantenimiento,
        db_item.id_item,
        db_evidencia.id_checklist_evidencia,
    )  # type: ignore[return-value]


def update_checklist_item_evidencia(
    db: Session,
    db_evidencia: MantenimientoChecklistEvidencia,
    evidencia_in: MantenimientoChecklistEvidenciaUpdate,
) -> MantenimientoChecklistEvidencia:
    update_data = evidencia_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_evidencia, field, value)
    db.commit()
    db.refresh(db_evidencia)
    return db_evidencia


def soft_delete_checklist_item_evidencia(
    db: Session,
    db_evidencia: MantenimientoChecklistEvidencia,
) -> MantenimientoChecklistEvidencia:
    db_evidencia.activo = False
    db.commit()
    db.refresh(db_evidencia)
    return db_evidencia
