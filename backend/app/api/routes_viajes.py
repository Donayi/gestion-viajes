from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

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
    finalizar_viaje,
    get_archivos_storage_prueba,
    get_asignaciones_by_viaje,
    get_asignaciones_enriched_by_viaje,
    get_cajas_disponibles,
    get_documentos_by_caja,
    get_documentos_by_operador,
    get_documentos_by_trailer,
    get_documentos_by_viaje,
    get_evidencia_by_id_and_viaje,
    get_evidencias_by_viaje,
    get_historial_by_viaje,
    get_historial_enriched_by_viaje,
    get_operadores_disponibles,
    get_tipos_documento,
    get_tipos_evidencia,
    get_trailers_disponibles,
    get_transiciones_disponibles_by_viaje,
    get_viaje_detail_by_id,
    get_viaje_by_folio,
    get_viaje_by_id,
    get_viajes,
    get_viajes_enriched,
    iniciar_carga_viaje,
    iniciar_viaje,
    marcar_retraso_viaje,
    operador_exists,
    poner_standby_viaje,
    reasignar_viaje,
    trailer_exists,
    tipo_documento_exists,
    tipo_evidencia_exists,
    usuario_exists,
    update_evidencia_viaje,
    update_viaje,
)
from app.db.deps import get_db
from app.schemas.documento import DocumentoCreate, DocumentoResponse, TipoDocumentoResponse
from app.schemas.evidencia import (
    ArchivoStoragePruebaResponse,
    TipoEvidenciaResponse,
    ViajeEvidenciaCreate,
    ViajeEvidenciaResponse,
    ViajeEvidenciaUpdate,
)
from app.schemas.viaje_view import ViajeDetailResponse, ViajeListItemResponse
from app.schemas.viaje_view import (
    HistorialEstatusViajeEnrichedResponse,
    ViajeAsignacionEnrichedResponse,
)
from app.schemas.viaje import (
    CajaDisponibleResponse,
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


@router.post("/", response_model=ViajeResponse, status_code=status.HTTP_201_CREATED)
def create_new_viaje(
    viaje_in: ViajeCreate,
    created_by: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    existing_viaje = get_viaje_by_folio(db, viaje_in.folio)
    if existing_viaje:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un viaje con ese folio",
        )

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
):
    return get_viajes(db, skip=skip, limit=limit)


@router.get("/enriched", response_model=list[ViajeListItemResponse])
def list_viajes_enriched(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return get_viajes_enriched(db, skip=skip, limit=limit)


@router.get(
    "/catalogos/tipos-evidencia",
    response_model=list[TipoEvidenciaResponse],
)
def list_tipos_evidencia(db: Session = Depends(get_db)):
    return get_tipos_evidencia(db)


@router.get(
    "/catalogos/tipos-documento",
    response_model=list[TipoDocumentoResponse],
)
def list_tipos_documento(db: Session = Depends(get_db)):
    return get_tipos_documento(db)


@router.get(
    "/archivos-prueba",
    response_model=list[ArchivoStoragePruebaResponse],
)
def list_archivos_prueba(db: Session = Depends(get_db)):
    return get_archivos_storage_prueba(db)


@router.get("/{viaje_id}", response_model=ViajeResponse)
def get_viaje(viaje_id: int, db: Session = Depends(get_db)):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    return db_viaje


@router.get("/{viaje_id}/detail", response_model=ViajeDetailResponse)
def get_viaje_detail(viaje_id: int, db: Session = Depends(get_db)):
    db_viaje = get_viaje_detail_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )
    return db_viaje


@router.put("/{viaje_id}", response_model=ViajeResponse)
def update_existing_viaje(
    viaje_id: int,
    viaje_in: ViajeUpdate,
    db: Session = Depends(get_db),
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

    return update_viaje(db, db_viaje, viaje_in)


@router.post(
    "/{viaje_id}/asignaciones",
    response_model=ViajeAsignacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_asignacion_viaje(
    viaje_id: int,
    asignacion_in: ViajeAsignacionCreate,
    db: Session = Depends(get_db),
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
def list_asignaciones_by_viaje(viaje_id: int, db: Session = Depends(get_db)):
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
def list_asignaciones_enriched_by_viaje(viaje_id: int, db: Session = Depends(get_db)):
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
def list_historial_estatus_by_viaje(viaje_id: int, db: Session = Depends(get_db)):
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
def list_historial_estatus_enriched_by_viaje(viaje_id: int, db: Session = Depends(get_db)):
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
):
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
def list_documentos_by_viaje(viaje_id: int, db: Session = Depends(get_db)):
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
):
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
def list_documentos_operador_actual(viaje_id: int, db: Session = Depends(get_db)):
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
):
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
def list_documentos_trailer_actual(viaje_id: int, db: Session = Depends(get_db)):
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
):
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
def list_documentos_caja_actual(viaje_id: int, db: Session = Depends(get_db)):
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
):
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
def list_evidencias_by_viaje(viaje_id: int, db: Session = Depends(get_db)):
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
def get_evidencia(viaje_id: int, evidencia_id: int, db: Session = Depends(get_db)):
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
):
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
def delete_evidencia(viaje_id: int, evidencia_id: int, db: Session = Depends(get_db)):
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
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return cambiar_estatus_viaje(db, db_viaje, cambio_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/disponibilidad/operadores",
    response_model=list[OperadorDisponibleResponse],
)
def list_operadores_disponibles(db: Session = Depends(get_db)):
    return get_operadores_disponibles(db)


@router.get(
    "/disponibilidad/trailers",
    response_model=list[TrailerDisponibleResponse],
)
def list_trailers_disponibles(db: Session = Depends(get_db)):
    return get_trailers_disponibles(db)


@router.get(
    "/disponibilidad/cajas",
    response_model=list[CajaDisponibleResponse],
)
def list_cajas_disponibles(db: Session = Depends(get_db)):
    return get_cajas_disponibles(db)

@router.get(
    "/{viaje_id}/transiciones-disponibles",
    response_model=list[TransicionDisponibleResponse],
)
def list_transiciones_disponibles(viaje_id: int, db: Session = Depends(get_db)):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

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
    accion_in: ViajeComentarioAccion,
    db: Session = Depends(get_db),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return iniciar_carga_viaje(
            db,
            db_viaje,
            changed_by=accion_in.changed_by,
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
    accion_in: ViajeComentarioAccion,
    db: Session = Depends(get_db),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return iniciar_viaje(
            db,
            db_viaje,
            changed_by=accion_in.changed_by,
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
    accion_in: ViajeComentarioAccion,
    db: Session = Depends(get_db),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return marcar_retraso_viaje(
            db,
            db_viaje,
            changed_by=accion_in.changed_by,
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
    accion_in: ViajeComentarioAccion,
    db: Session = Depends(get_db),
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
            changed_by=accion_in.changed_by,
            comentario=accion_in.comentario,
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
    accion_in: ViajeComentarioAccion,
    db: Session = Depends(get_db),
):
    db_viaje = get_viaje_by_id(db, viaje_id)
    if not db_viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Viaje no encontrado",
        )

    try:
        return finalizar_viaje(
            db,
            db_viaje,
            changed_by=accion_in.changed_by,
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
            changed_by=accion_in.changed_by,
            comentario=accion_in.comentario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
