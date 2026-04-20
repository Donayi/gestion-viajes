from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.crud_viajes import (
    caja_exists,
    cancelar_viaje,
    cambiar_estatus_viaje,
    cliente_exists,
    create_asignacion_viaje,
    create_viaje,
    finalizar_viaje,
    get_asignaciones_by_viaje,
    get_cajas_disponibles,
    get_historial_by_viaje,
    get_operadores_disponibles,
    get_trailers_disponibles,
    get_transiciones_disponibles_by_viaje,
    get_viaje_by_folio,
    get_viaje_by_id,
    get_viajes,
    iniciar_carga_viaje,
    iniciar_viaje,
    marcar_retraso_viaje,
    operador_exists,
    poner_standby_viaje,
    reasignar_viaje,
    trailer_exists,
    update_viaje,
)
from app.db.deps import get_db
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


@router.get("/{viaje_id}", response_model=ViajeResponse)
def get_viaje(viaje_id: int, db: Session = Depends(get_db)):
    db_viaje = get_viaje_by_id(db, viaje_id)
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