from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.crud.crud_alertas import (
    generar_alertas,
    get_alerta_by_id,
    get_alertas,
    mark_alerta_as_read,
    procesar_notificaciones_pendientes,
)
from app.db.deps import get_db
from app.models.models import Usuario
from app.schemas.alerta import AlertaResponse, GenerarAlertasResponse
from app.schemas.telegram import ProcesarNotificacionesResponse


router = APIRouter(prefix="/alertas", tags=["Alertas"])


@router.get("", response_model=list[AlertaResponse])
def list_alertas(
    tipo_alerta: str | None = Query(default=None),
    nivel: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    return get_alertas(db, tipo_alerta=tipo_alerta, nivel=nivel)


@router.patch("/{alerta_id}/leer", response_model=AlertaResponse)
def mark_alerta_read(
    alerta_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    db_alerta = get_alerta_by_id(db, alerta_id)
    if not db_alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta no encontrada",
        )
    return mark_alerta_as_read(db, db_alerta)


@router.post("/generar", response_model=GenerarAlertasResponse)
def run_generar_alertas(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    return generar_alertas(db)


@router.post("/notificar-pendientes", response_model=ProcesarNotificacionesResponse)
def run_notificar_alertas_pendientes(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    return procesar_notificaciones_pendientes(db)
