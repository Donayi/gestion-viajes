from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps_auth import is_admin_user, require_admin, require_admin_or_operador
from app.crud.crud_kpis import get_kpis_operativos_dashboard
from app.crud.crud_viajes import (
    archivo_storage_exists,
    caja_exists,
    cancelar_viaje,
    cambiar_estatus_viaje,
    cliente_exists,
    create_documento_caja_actual_viaje,
    create_documento_operador_actual_viaje,
    create_documento_trailer_actual_viaje,
    create_documento_viaje,
    create_evidencia_viaje,
    create_asignacion_viaje,
    create_viaje,
    delete_evidencia_viaje,
    get_solicitud_standby_pendiente,
    finalizar_viaje,
    get_archivos_storage_prueba,
    get_asignaciones_by_viaje,
    get_asignaciones_enriched_by_viaje,
    get_cajas_disponibles,
    get_disponibilidad_resumen,
    get_documentos_by_caja,
    get_documentos_by_operador,
    get_documentos_by_trailer,
    get_documentos_by_viaje,
    get_evidencia_by_id_and_viaje,
    get_evidencias_by_viaje,
    get_eventos_operativos_by_viaje,
    get_historial_by_viaje,
    get_historial_enriched_by_viaje,
    get_operadores_disponibles,
    _viaje_listo_para_reinicio,
    get_tipos_documento,
    get_tipos_evidencia,
    get_trailers_disponibles,
    get_transiciones_disponibles_by_viaje,
    get_viaje_detail_by_id,
    get_viaje_by_folio,
    get_viaje_by_id,
    get_viajes,
    get_viajes_enriched,
    get_viajes_mapa,
    get_viajes_visibles_para_operador,
    iniciar_carga_viaje,
    iniciar_viaje,
    marcar_retraso_viaje,
    operador_puede_operar_viaje,
    operador_puede_ver_viaje,
    operador_exists,
    poner_standby_viaje,
    reasignar_viaje,
    solicitar_standby_viaje,
    autorizar_standby_viaje,
    trailer_exists,
    tipo_documento_exists,
    tipo_evidencia_exists,
    usuario_exists,
    get_evento_operativo_by_id_and_viaje,
    update_evidencia_viaje,
    update_evento_operativo_viaje,
    update_viaje,
    reiniciar_viaje,
)
from app.db.deps import get_db
from app.models.models import Usuario
from app.schemas.documento import DocumentoCreate, DocumentoResponse, TipoDocumentoResponse
from app.schemas.evidencia import (
    ArchivoStoragePruebaResponse,
    TipoEvidenciaResponse,
    ViajeEvidenciaCreate,
    ViajeEvidenciaResponse,
    ViajeEvidenciaUpdate,
)
from app.schemas.evento_operativo import (
    EventoOperativoCargaPayload,
    EventoOperativoRetrasoPayload,
    EventoOperativoViajePayload,
    EventoOperativoViajeResponse,
    EventoOperativoViajeUpdatePayload,
)
from app.schemas.kpi_operativo import KpiOperativoDashboardResponse, KpiOperativoFilterParams
from app.schemas.viaje_view import ViajeDetailResponse, ViajeListItemResponse, ViajeMapaItemResponse
from app.schemas.viaje_view import (
    HistorialEstatusViajeEnrichedResponse,
    ViajeAsignacionEnrichedResponse,
)
from app.schemas.viaje import (
    CambioEstatusResponse,
    CajaDisponibleResponse,
    DisponibilidadResumenResponse,
    HistorialEstatusViajeResponse,
    OperadorDisponibleResponse,
    TrailerDisponibleResponse,
    TransicionDisponibleResponse,
    ViajeAsignacionCreate,
    ViajeAsignacionResponse,
    ViajeCambioEstatus,
    ViajeComentarioAccion,
    ViajeCreate,
    ViajeReasignacionCreate,
    ViajeResponse,
    ViajeUpdate,
)

router = APIRouter(prefix="/viajes", tags=["Viajes"])


def _usuario_es_admin(current_user: Usuario) -> bool:
    return is_admin_user(current_user)


def _validar_acceso_viaje(
    db: Session,
    viaje_id: int,
    current_user: Usuario,
    requiere_operacion: bool = False,
) -> None:
    if _usuario_es_admin(current_user):
        return

    if current_user.operador is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario actual no tiene perfil de operador",
        )

    operador_id = current_user.operador.id_operador
    permitido = (
        operador_puede_operar_viaje(db, operador_id, viaje_id)
        if requiere_operacion
        else operador_puede_ver_viaje(db, operador_id, viaje_id)
    )

    if not permitido:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este viaje",
        )


def _resolve_changed_by(current_user: Usuario, requested_changed_by: int | None) -> int | None:
    return requested_changed_by or current_user.id_usuario


def _bloquear_operacion_operador_en_standby(db_viaje, current_user: Usuario) -> None:
    if _usuario_es_admin(current_user):
        return

    estatus_actual = db_viaje.estatus_actual
    if estatus_actual and estatus_actual.clave == "STANDBY":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viaje en standby, pendiente de reasignación administrativa",
        )


@router.post("/", response_model=ViajeResponse, status_code=status.HTTP_201_CREATED)
def create_new_viaje(
    viaje_in: ViajeCreate,
    created_by: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if not cliente_exists(db, viaje_in.id_cliente):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente especificado no existe",
        )

    try:
        return create_viaje(db, viaje_in, created_by=created_by)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/", response_model=list[ViajeResponse])
def list_viajes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    if _usuario_es_admin(current_user):
        return get_viajes(db, skip=skip, limit=limit)

    return get_viajes_visibles_para_operador(
        db,
        current_user.operador.id_operador,
        skip=skip,
        limit=limit,
    )


@router.get("/enriched", response_model=list[ViajeListItemResponse])
def list_viajes_enriched(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    if _usuario_es_admin(current_user):
        return get_viajes_enriched(db, skip=skip, limit=limit)

    return get_viajes_visibles_para_operador(
        db,
        current_user.operador.id_operador,
        skip=skip,
        limit=limit,
    )


@router.get("/mapa", response_model=list[ViajeMapaItemResponse])
def list_viajes_mapa(
    estatus: list[str] | None = Query(default=None),
    incluir_finalizados: bool = Query(default=True),
    incluir_cancelados: bool = Query(default=False),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_viajes_mapa(
        db,
        estatus_claves=estatus,
        incluir_finalizados=incluir_finalizados,
        incluir_cancelados=incluir_cancelados,
    )


@router.get(
    "/catalogos/tipos-evidencia",
    response_model=list[TipoEvidenciaResponse],
)
def list_tipos_evidencia(
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_operador),
):
    return get_tipos_evidencia(db)


@router.get(
    "/catalogos/tipos-documento",
    response_model=list[TipoDocumentoResponse],
)
def list_tipos_documento(
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_operador),
):
    return get_tipos_documento(db)


@router.get(
    "/archivos-prueba",
    response_model=list[ArchivoStoragePruebaResponse],
)
def list_archivos_prueba(
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_operador),
):
    return get_archivos_storage_prueba(db)


@router.get(
    "/kpis-operativos",
    response_model=KpiOperativoDashboardResponse,
)
def get_kpis_operativos(
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    id_operador: int | None = Query(default=None),
    id_cliente: int | None = Query(default=None),
    id_estatus: int | None = Query(default=None),
    solo_completos: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    filters = KpiOperativoFilterParams(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        id_operador=(
            current_user.operador.id_operador
            if not _usuario_es_admin(current_user) and current_user.operador is not None
            else id_operador
        ),
        id_cliente=id_cliente,
        id_estatus=id_estatus,
        solo_completos=solo_completos,
    )

    if not _usuario_es_admin(current_user) and current_user.operador is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario actual no tiene perfil de operador",
        )

    return get_kpis_operativos_dashboard(db, filters)


@router.get("/{viaje_id}", response_model=ViajeResponse)
def get_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    return db_viaje


@router.get("/{viaje_id}/detail", response_model=ViajeDetailResponse)
def get_viaje_detail(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_detail_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    setattr(
        db_viaje,
        "solicitud_standby_pendiente",
        get_solicitud_standby_pendiente(db, db_viaje) is not None,
    )
    setattr(
        db_viaje,
        "requiere_reinicio_viaje",
        _viaje_listo_para_reinicio(db, db_viaje),
    )
    return db_viaje


@router.get(
    "/{viaje_id}/eventos-operativos",
    response_model=list[EventoOperativoViajeResponse],
)
def list_eventos_operativos_by_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    return get_eventos_operativos_by_viaje(db, viaje_id)


@router.put(
    "/{viaje_id}/eventos-operativos/{evento_id}",
    response_model=EventoOperativoViajeResponse,
)
def update_evento_operativo(
    viaje_id: int,
    evento_id: int,
    evento_in: EventoOperativoViajeUpdatePayload,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if db_viaje.estatus_actual and db_viaje.estatus_actual.es_terminal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El viaje ya está {db_viaje.estatus_actual.clave} y no admite nuevas acciones operativas.",
        )

    db_evento = get_evento_operativo_by_id_and_viaje(db, viaje_id, evento_id)
    if not db_evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento operativo no encontrado para el viaje especificado",
        )

    try:
        return update_evento_operativo_viaje(db, db_evento, evento_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put("/{viaje_id}", response_model=ViajeResponse)
def update_existing_viaje(
    viaje_id: int,
    viaje_in: ViajeUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if viaje_in.id_cliente is not None and not cliente_exists(db, viaje_in.id_cliente):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente especificado no existe",
        )

    if viaje_in.folio is not None:
        existing_viaje = get_viaje_by_folio(db, viaje_in.folio)
        if existing_viaje and existing_viaje.id_viaje != viaje_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro viaje con ese folio",
            )

    payload = viaje_in.model_dump(exclude_unset=True)
    forbidden_fields = {
        "id_estatus_actual",
        "id_operador_actual",
        "id_trailer_actual",
        "id_caja_actual",
        "fecha_inicio",
        "fecha_llegada",
    }
    attempted_forbidden = sorted(
        field for field in forbidden_fields if payload.get(field) is not None
    )
    if attempted_forbidden:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La edición administrativa no permite cambiar estatus, "
                "asignación actual ni fechas operativas directamente"
            ),
        )

    sanitized_payload = {field: value for field, value in payload.items() if field not in forbidden_fields}
    sanitized_payload["updated_by"] = _resolve_changed_by(current_user, viaje_in.updated_by)

    return update_viaje(db, db_viaje, ViajeUpdate(**sanitized_payload))


@router.post(
    "/{viaje_id}/asignaciones",
    response_model=ViajeAsignacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_asignacion_viaje(
    viaje_id: int,
    asignacion_in: ViajeAsignacionCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not operador_exists(db, asignacion_in.id_operador):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El operador especificado no existe",
        )

    if not trailer_exists(db, asignacion_in.id_trailer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tráiler especificado no existe",
        )

    if asignacion_in.id_caja is not None and not caja_exists(db, asignacion_in.id_caja):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La caja especificada no existe",
        )

    try:
        return create_asignacion_viaje(db, db_viaje, asignacion_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{viaje_id}/asignaciones",
    response_model=list[ViajeAsignacionResponse],
)
def list_asignaciones_by_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    return get_asignaciones_by_viaje(db, viaje_id)


@router.get(
    "/{viaje_id}/asignaciones/enriched",
    response_model=list[ViajeAsignacionEnrichedResponse],
)
def list_asignaciones_enriched_by_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    return get_asignaciones_enriched_by_viaje(db, viaje_id)


@router.get(
    "/{viaje_id}/historial-estatus",
    response_model=list[HistorialEstatusViajeResponse],
)
def list_historial_estatus_by_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    return get_historial_by_viaje(db, viaje_id)


@router.get(
    "/{viaje_id}/historial-estatus/enriched",
    response_model=list[HistorialEstatusViajeEnrichedResponse],
)
def list_historial_estatus_enriched_by_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    return get_historial_enriched_by_viaje(db, viaje_id)


@router.post(
    "/{viaje_id}/documentos",
    response_model=DocumentoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_documento_viaje(
    viaje_id: int,
    documento_in: DocumentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not tipo_documento_exists(db, documento_in.id_tipo_documento):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de documento especificado no existe",
        )

    if not archivo_storage_exists(db, documento_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    if documento_in.subido_por is not None and not usuario_exists(db, documento_in.subido_por):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario que sube el documento no existe",
        )

    try:
        return create_documento_viaje(db, db_viaje, documento_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{viaje_id}/documentos",
    response_model=list[DocumentoResponse],
)
def list_documentos_by_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    return get_documentos_by_viaje(db, viaje_id)


@router.post(
    "/{viaje_id}/operador-actual/documentos",
    response_model=DocumentoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_documento_operador_actual(
    viaje_id: int,
    documento_in: DocumentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not tipo_documento_exists(db, documento_in.id_tipo_documento):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de documento especificado no existe",
        )

    if not archivo_storage_exists(db, documento_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    if documento_in.subido_por is not None and not usuario_exists(db, documento_in.subido_por):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario que sube el documento no existe",
        )

    try:
        return create_documento_operador_actual_viaje(db, db_viaje, documento_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{viaje_id}/operador-actual/documentos",
    response_model=list[DocumentoResponse],
)
def list_documentos_operador_actual(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    if not db_viaje.operador_actual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El viaje no tiene operador actual para consultar documentos",
        )

    return get_documentos_by_operador(db, db_viaje.operador_actual.id_operador)


@router.post(
    "/{viaje_id}/trailer-actual/documentos",
    response_model=DocumentoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_documento_trailer_actual(
    viaje_id: int,
    documento_in: DocumentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not tipo_documento_exists(db, documento_in.id_tipo_documento):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de documento especificado no existe",
        )

    if not archivo_storage_exists(db, documento_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    if documento_in.subido_por is not None and not usuario_exists(db, documento_in.subido_por):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario que sube el documento no existe",
        )

    try:
        return create_documento_trailer_actual_viaje(db, db_viaje, documento_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{viaje_id}/trailer-actual/documentos",
    response_model=list[DocumentoResponse],
)
def list_documentos_trailer_actual(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    if not db_viaje.trailer_actual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El viaje no tiene tráiler actual para consultar documentos",
        )

    return get_documentos_by_trailer(db, db_viaje.trailer_actual.id_trailer)


@router.post(
    "/{viaje_id}/caja-actual/documentos",
    response_model=DocumentoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_documento_caja_actual(
    viaje_id: int,
    documento_in: DocumentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not tipo_documento_exists(db, documento_in.id_tipo_documento):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de documento especificado no existe",
        )

    if not archivo_storage_exists(db, documento_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    if documento_in.subido_por is not None and not usuario_exists(db, documento_in.subido_por):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario que sube el documento no existe",
        )

    try:
        return create_documento_caja_actual_viaje(db, db_viaje, documento_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{viaje_id}/caja-actual/documentos",
    response_model=list[DocumentoResponse],
)
def list_documentos_caja_actual(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    if not db_viaje.caja_actual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El viaje no tiene caja actual para consultar documentos",
        )

    return get_documentos_by_caja(db, db_viaje.caja_actual.id_caja)


@router.post(
    "/{viaje_id}/evidencias",
    response_model=ViajeEvidenciaResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_evidencia_viaje(
    viaje_id: int,
    evidencia_in: ViajeEvidenciaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not tipo_evidencia_exists(db, evidencia_in.id_tipo_evidencia):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de evidencia especificado no existe",
        )

    if not archivo_storage_exists(db, evidencia_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    if evidencia_in.id_operador is not None and not operador_exists(db, evidencia_in.id_operador):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El operador especificado no existe",
        )

    if (
        evidencia_in.id_evento_operativo is not None
        and not get_evento_operativo_by_id_and_viaje(db, viaje_id, evidencia_in.id_evento_operativo)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento operativo especificado no pertenece al viaje",
        )

    try:
        return create_evidencia_viaje(db, db_viaje, evidencia_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{viaje_id}/evidencias",
    response_model=list[ViajeEvidenciaResponse],
)
def list_evidencias_by_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    return get_evidencias_by_viaje(db, viaje_id)


@router.get(
    "/{viaje_id}/evidencias/{evidencia_id}",
    response_model=ViajeEvidenciaResponse,
)
def get_evidencia(
    viaje_id: int,
    evidencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    db_evidencia = get_evidencia_by_id_and_viaje(db, evidencia_id, viaje_id)
    if not db_evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada para el viaje especificado",
        )

    return db_evidencia


@router.put(
    "/{viaje_id}/evidencias/{evidencia_id}",
    response_model=ViajeEvidenciaResponse,
)
def update_evidencia(
    viaje_id: int,
    evidencia_id: int,
    evidencia_in: ViajeEvidenciaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    db_evidencia = get_evidencia_by_id_and_viaje(db, evidencia_id, viaje_id)
    if not db_evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada para el viaje especificado",
        )

    if (
        evidencia_in.id_tipo_evidencia is not None
        and not tipo_evidencia_exists(db, evidencia_in.id_tipo_evidencia)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de evidencia especificado no existe",
        )

    if evidencia_in.id_archivo is not None and not archivo_storage_exists(db, evidencia_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    if evidencia_in.id_operador is not None and not operador_exists(db, evidencia_in.id_operador):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El operador especificado no existe",
        )

    if (
        evidencia_in.id_evento_operativo is not None
        and not get_evento_operativo_by_id_and_viaje(db, viaje_id, evidencia_in.id_evento_operativo)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento operativo especificado no pertenece al viaje",
        )

    try:
        return update_evidencia_viaje(db, db_evidencia, evidencia_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{viaje_id}/evidencias/{evidencia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_evidencia(
    viaje_id: int,
    evidencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    db_evidencia = get_evidencia_by_id_and_viaje(db, evidencia_id, viaje_id)
    if not db_evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada para el viaje especificado",
        )

    delete_evidencia_viaje(db, db_evidencia)
    return None


@router.post("/{viaje_id}/cambiar-estatus", response_model=ViajeResponse)
def cambiar_estatus(
    viaje_id: int,
    cambio_in: ViajeCambioEstatus,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    _bloquear_operacion_operador_en_standby(db_viaje, current_user)

    try:
        return cambiar_estatus_viaje(db, db_viaje, cambio_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/disponibilidad/resumen",
    response_model=DisponibilidadResumenResponse,
)
def get_disponibilidad_planeacion(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_disponibilidad_resumen(db)


@router.get(
    "/disponibilidad/operadores",
    response_model=list[OperadorDisponibleResponse],
)
def list_operadores_disponibles(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_operadores_disponibles(db)


@router.get(
    "/disponibilidad/trailers",
    response_model=list[TrailerDisponibleResponse],
)
def list_trailers_disponibles(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_trailers_disponibles(db)


@router.get(
    "/disponibilidad/cajas",
    response_model=list[CajaDisponibleResponse],
)
def list_cajas_disponibles(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_cajas_disponibles(db)

@router.get(
    "/{viaje_id}/transiciones-disponibles",
    response_model=list[TransicionDisponibleResponse],
)
def list_transiciones_disponibles(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if db_viaje.estatus_actual and db_viaje.estatus_actual.es_terminal:
        return []

    if not _usuario_es_admin(current_user) and db_viaje.estatus_actual and db_viaje.estatus_actual.clave == "STANDBY":
        return []

    transiciones = get_transiciones_disponibles_by_viaje(db, db_viaje)

    return [
        TransicionDisponibleResponse(
            id_estatus_destino=t.estatus_destino.id_estatus,
            clave=t.estatus_destino.clave,
            nombre=t.estatus_destino.nombre,
            requiere_comentario=t.requiere_comentario,
            requiere_evidencia=t.requiere_evidencia,
        )
        for t in transiciones
    ]


@router.post("/{viaje_id}/asignar", response_model=ViajeAsignacionResponse)
def asignar_viaje(
    viaje_id: int,
    asignacion_in: ViajeAsignacionCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not operador_exists(db, asignacion_in.id_operador):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El operador especificado no existe",
        )

    if not trailer_exists(db, asignacion_in.id_trailer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tráiler especificado no existe",
        )

    if asignacion_in.id_caja is not None and not caja_exists(db, asignacion_in.id_caja):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La caja especificada no existe",
        )

    try:
        return create_asignacion_viaje(db, db_viaje, asignacion_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/iniciar-carga", response_model=ViajeResponse)
def iniciar_carga(
    viaje_id: int,
    accion_in: EventoOperativoCargaPayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    _bloquear_operacion_operador_en_standby(db_viaje, current_user)

    try:
        return iniciar_carga_viaje(
            db,
            db_viaje,
            evento_in=accion_in,
            changed_by=_resolve_changed_by(current_user, None),
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/iniciar-viaje", response_model=ViajeResponse)
def iniciar_viaje_endpoint(
    viaje_id: int,
    accion_in: EventoOperativoViajePayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    _bloquear_operacion_operador_en_standby(db_viaje, current_user)

    try:
        return iniciar_viaje(
            db,
            db_viaje,
            evento_in=accion_in,
            changed_by=_resolve_changed_by(current_user, None),
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/marcar-retraso", response_model=ViajeResponse)
def marcar_retraso(
    viaje_id: int,
    accion_in: EventoOperativoRetrasoPayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    _bloquear_operacion_operador_en_standby(db_viaje, current_user)

    try:
        return marcar_retraso_viaje(
            db,
            db_viaje,
            evento_in=accion_in,
            changed_by=_resolve_changed_by(current_user, None),
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/poner-standby", response_model=ViajeResponse)
def poner_standby(
    viaje_id: int,
    accion_in: EventoOperativoViajePayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return poner_standby_viaje(
            db,
            db_viaje,
            evento_in=accion_in,
            changed_by=_resolve_changed_by(current_user, None),
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/solicitar-standby", response_model=CambioEstatusResponse)
def solicitar_standby(
    viaje_id: int,
    accion_in: EventoOperativoViajePayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    if _usuario_es_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un operador puede solicitar standby desde esta ruta",
        )

    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        solicitar_standby_viaje(
            db,
            db_viaje,
            evento_in=accion_in,
            changed_by=_resolve_changed_by(current_user, None),
        )
        return CambioEstatusResponse(
            id_viaje=db_viaje.id_viaje,
            id_estatus_actual=db_viaje.id_estatus_actual,
            mensaje="Solicitud registrada, pendiente de autorización administrativa",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/reiniciar-viaje", response_model=ViajeResponse)
def reiniciar_viaje_endpoint(
    viaje_id: int,
    accion_in: EventoOperativoViajePayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return reiniciar_viaje(
            db,
            db_viaje,
            evento_in=accion_in,
            changed_by=_resolve_changed_by(current_user, None),
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/autorizar-standby", response_model=ViajeResponse)
def autorizar_standby(
    viaje_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not get_solicitud_standby_pendiente(db, db_viaje):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existe una solicitud de standby pendiente para este viaje",
        )

    try:
        return autorizar_standby_viaje(
            db,
            db_viaje,
            changed_by=_resolve_changed_by(current_user, None),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/reasignar", response_model=ViajeAsignacionResponse)
def reasignar(
    viaje_id: int,
    reasignacion_in: ViajeReasignacionCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    if not operador_exists(db, reasignacion_in.id_operador):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El operador especificado no existe",
        )

    if not trailer_exists(db, reasignacion_in.id_trailer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tráiler especificado no existe",
        )

    if reasignacion_in.id_caja is not None and not caja_exists(db, reasignacion_in.id_caja):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La caja especificada no existe",
        )

    asignacion = ViajeAsignacionCreate(
        id_operador=reasignacion_in.id_operador,
        id_trailer=reasignacion_in.id_trailer,
        id_caja=reasignacion_in.id_caja,
        created_by=reasignacion_in.created_by,
        motivo=reasignacion_in.motivo,
        comentario=reasignacion_in.comentario,
    )

    try:
        return reasignar_viaje(db, db_viaje, asignacion)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/finalizar", response_model=ViajeResponse)
def finalizar(
    viaje_id: int,
    accion_in: EventoOperativoViajePayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    _validar_acceso_viaje(db, viaje_id, current_user, requiere_operacion=True)
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    _bloquear_operacion_operador_en_standby(db_viaje, current_user)

    try:
        return finalizar_viaje(
            db,
            db_viaje,
            evento_in=accion_in,
            changed_by=_resolve_changed_by(current_user, None),
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{viaje_id}/cancelar", response_model=ViajeResponse)
def cancelar(
    viaje_id: int,
    accion_in: ViajeComentarioAccion,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return cancelar_viaje(
            db,
            db_viaje,
            changed_by=_resolve_changed_by(current_user, accion_in.changed_by),
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
