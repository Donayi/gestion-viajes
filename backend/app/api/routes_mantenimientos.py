from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps_auth import (
    is_admin_user,
    is_mantenimiento_user,
    require_admin,
    require_admin_or_mantenimiento,
    require_mantenimiento,
)
from app.crud.crud_mantenimientos import (
    archivo_storage_exists,
    caja_exists,
    cancelar_mantenimiento,
    cerrar_mantenimiento,
    create_checklist_item_evidencia,
    create_mantenimiento,
    create_mantenimiento_archivo,
    get_checklist_item_by_id,
    get_checklist_item_evidencia_by_id,
    get_checklist_item_evidencias,
    get_mantenimiento_by_id,
    get_mantenimiento_archivo_by_id,
    get_mantenimiento_archivos,
    get_mantenimientos,
    soft_delete_checklist_item_evidencia,
    soft_delete_mantenimiento_archivo,
    trailer_exists,
    update_checklist_item_evidencia,
    update_mantenimiento_archivo,
    update_mantenimiento,
    update_mantenimiento_checklist_item,
)
from app.crud.crud_viajes import get_cajas_disponibles, get_trailers_disponibles
from app.db.deps import get_db
from app.models.models import Usuario
from app.schemas.mantenimiento import (
    EntidadMantenimientoTipo,
    MantenimientoArchivoCreate,
    MantenimientoArchivoResponse,
    MantenimientoArchivoUpdate,
    MantenimientoCambioEstado,
    MantenimientoChecklistEvidenciaCreate,
    MantenimientoChecklistEvidenciaResponse,
    MantenimientoChecklistEvidenciaUpdate,
    MantenimientoChecklistItemResponse,
    MantenimientoChecklistItemUpdate,
    MantenimientoCreate,
    MantenimientoRecursosDisponiblesResponse,
    MantenimientoResponse,
    MantenimientoUpdate,
)


router = APIRouter(prefix="/mantenimientos", tags=["Mantenimientos"])
OWNERSHIP_ERROR_DETAIL = "No tienes permiso para operar esta orden de mantenimiento."


def _validar_entidad(entidad_tipo: EntidadMantenimientoTipo, entidad_id: int, db: Session) -> None:
    existe = trailer_exists(db, entidad_id) if entidad_tipo == "TRAILER" else caja_exists(db, entidad_id)
    if not existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El recurso especificado no existe",
        )


def _assert_mantenimiento_ownership(db_mantenimiento, current_user: Usuario) -> None:
    if is_admin_user(current_user):
        return
    if is_mantenimiento_user(current_user) and db_mantenimiento.created_by == current_user.id_usuario:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=OWNERSHIP_ERROR_DETAIL,
    )


@router.get("", response_model=list[MantenimientoResponse])
def list_mantenimientos(
    entidad_tipo: EntidadMantenimientoTipo | None = Query(default=None),
    estatus: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_mantenimiento),
):
    created_by = current_user.id_usuario if is_mantenimiento_user(current_user) and not is_admin_user(current_user) else None
    return get_mantenimientos(db, entidad_tipo=entidad_tipo, estatus=estatus, created_by=created_by)


@router.get("/recursos-disponibles", response_model=MantenimientoRecursosDisponiblesResponse)
def list_recursos_disponibles_para_mantenimiento(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin_or_mantenimiento),
):
    return MantenimientoRecursosDisponiblesResponse(
        trailers=get_trailers_disponibles(db),
        cajas=get_cajas_disponibles(db),
    )


@router.get("/{mantenimiento_id}", response_model=MantenimientoResponse)
def get_mantenimiento(
    mantenimiento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, current_user)
    return db_mantenimiento


@router.post("", response_model=MantenimientoResponse, status_code=status.HTTP_201_CREATED)
def create_new_mantenimiento(
    mantenimiento_in: MantenimientoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_mantenimiento),
):
    _validar_entidad(mantenimiento_in.entidad_tipo, mantenimiento_in.entidad_id, db)
    try:
        return create_mantenimiento(db, mantenimiento_in, created_by=current_user.id_usuario)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put("/{mantenimiento_id}", response_model=MantenimientoResponse)
def update_existing_mantenimiento(
    mantenimiento_id: int,
    mantenimiento_in: MantenimientoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, current_user)
    if mantenimiento_in.estatus is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estatus del mantenimiento se controla con acciones dedicadas",
        )
    if mantenimiento_in.tipo_mantenimiento is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de mantenimiento no puede modificarse desde esta operación",
        )
    try:
        return update_mantenimiento(
            db,
            db_mantenimiento,
            mantenimiento_in,
            updated_by=current_user.id_usuario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{mantenimiento_id}/cerrar", response_model=MantenimientoResponse)
def close_mantenimiento(
    mantenimiento_id: int,
    cambio_in: MantenimientoCambioEstado,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, current_user)
    try:
        return cerrar_mantenimiento(
            db,
            db_mantenimiento,
            updated_by=current_user.id_usuario,
            observaciones=cambio_in.observaciones,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{mantenimiento_id}/cancelar", response_model=MantenimientoResponse)
def cancel_mantenimiento(
    mantenimiento_id: int,
    cambio_in: MantenimientoCambioEstado,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    try:
        return cancelar_mantenimiento(
            db,
            db_mantenimiento,
            updated_by=current_user.id_usuario,
            observaciones=cambio_in.observaciones,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/{mantenimiento_id}/checklist/{item_id}",
    response_model=MantenimientoChecklistItemResponse,
)
def update_checklist_item(
    mantenimiento_id: int,
    item_id: int,
    item_in: MantenimientoChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    try:
        return update_mantenimiento_checklist_item(
            db,
            db_mantenimiento,
            item_id,
            item_in,
            updated_by=current_user.id_usuario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{mantenimiento_id}/archivos", response_model=list[MantenimientoArchivoResponse])
def list_mantenimiento_archivos(
    mantenimiento_id: int,
    solo_activos: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, current_user)
    return get_mantenimiento_archivos(db, mantenimiento_id, solo_activos=solo_activos)


@router.post(
    "/{mantenimiento_id}/archivos",
    response_model=MantenimientoArchivoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_archivo_mantenimiento(
    mantenimiento_id: int,
    archivo_in: MantenimientoArchivoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, current_user)
    if not archivo_storage_exists(db, archivo_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )
    return create_mantenimiento_archivo(
        db,
        db_mantenimiento,
        archivo_in,
        created_by=current_user.id_usuario,
    )


@router.put(
    "/{mantenimiento_id}/archivos/{mantenimiento_archivo_id}",
    response_model=MantenimientoArchivoResponse,
)
def update_archivo_mantenimiento(
    mantenimiento_id: int,
    mantenimiento_archivo_id: int,
    archivo_in: MantenimientoArchivoUpdate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, _current_user)
    db_mantenimiento_archivo = get_mantenimiento_archivo_by_id(
        db,
        mantenimiento_id,
        mantenimiento_archivo_id,
    )
    if not db_mantenimiento_archivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo de mantenimiento no encontrado",
        )
    return update_mantenimiento_archivo(db, db_mantenimiento_archivo, archivo_in)


@router.delete(
    "/{mantenimiento_id}/archivos/{mantenimiento_archivo_id}",
    response_model=MantenimientoArchivoResponse,
)
def delete_archivo_mantenimiento(
    mantenimiento_id: int,
    mantenimiento_archivo_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, _current_user)
    db_mantenimiento_archivo = get_mantenimiento_archivo_by_id(
        db,
        mantenimiento_id,
        mantenimiento_archivo_id,
    )
    if not db_mantenimiento_archivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo de mantenimiento no encontrado",
    )
    return soft_delete_mantenimiento_archivo(db, db_mantenimiento_archivo)


@router.get(
    "/{mantenimiento_id}/checklist/{item_id}/evidencias",
    response_model=list[MantenimientoChecklistEvidenciaResponse],
)
def list_checklist_item_evidencias(
    mantenimiento_id: int,
    item_id: int,
    solo_activos: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, current_user)
    db_item = get_checklist_item_by_id(db, mantenimiento_id, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El item de checklist no pertenece al mantenimiento especificado",
        )
    return get_checklist_item_evidencias(db, mantenimiento_id, item_id, solo_activos=solo_activos)


@router.post(
    "/{mantenimiento_id}/checklist/{item_id}/evidencias",
    response_model=MantenimientoChecklistEvidenciaResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checklist_evidencia(
    mantenimiento_id: int,
    item_id: int,
    evidencia_in: MantenimientoChecklistEvidenciaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, current_user)
    db_item = get_checklist_item_by_id(db, mantenimiento_id, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El item de checklist no pertenece al mantenimiento especificado",
        )
    if not archivo_storage_exists(db, evidencia_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )
    return create_checklist_item_evidencia(db, db_item, evidencia_in, created_by=current_user.id_usuario)


@router.put(
    "/{mantenimiento_id}/checklist/{item_id}/evidencias/{checklist_evidencia_id}",
    response_model=MantenimientoChecklistEvidenciaResponse,
)
def update_checklist_evidencia(
    mantenimiento_id: int,
    item_id: int,
    checklist_evidencia_id: int,
    evidencia_in: MantenimientoChecklistEvidenciaUpdate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, _current_user)
    db_evidencia = get_checklist_item_evidencia_by_id(
        db,
        mantenimiento_id,
        item_id,
        checklist_evidencia_id,
    )
    if not db_evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia del rubro no encontrada",
        )
    return update_checklist_item_evidencia(db, db_evidencia, evidencia_in)


@router.delete(
    "/{mantenimiento_id}/checklist/{item_id}/evidencias/{checklist_evidencia_id}",
    response_model=MantenimientoChecklistEvidenciaResponse,
)
def delete_checklist_evidencia(
    mantenimiento_id: int,
    item_id: int,
    checklist_evidencia_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_mantenimiento),
):
    db_mantenimiento = get_mantenimiento_by_id(db, mantenimiento_id)
    if not db_mantenimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mantenimiento no encontrado",
        )
    _assert_mantenimiento_ownership(db_mantenimiento, _current_user)
    db_evidencia = get_checklist_item_evidencia_by_id(
        db,
        mantenimiento_id,
        item_id,
        checklist_evidencia_id,
    )
    if not db_evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia del rubro no encontrada",
        )
    return soft_delete_checklist_item_evidencia(db, db_evidencia)
