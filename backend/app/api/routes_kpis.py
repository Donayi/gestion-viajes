from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.crud.crud_kpis import (
    get_kpis_clientes,
    get_kpis_operadores,
    get_kpis_trailers,
)
from app.db.deps import get_db
from app.schemas.kpi_catalogado import (
    KpiClientesResponse,
    KpiOperadoresResponse,
    KpiTrailersResponse,
)

router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get("/operadores", response_model=KpiOperadoresResponse)
def list_kpis_operadores(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_operador: int | None = Query(default=None),
    nombre_operador: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_kpis_operadores(
        db,
        fecha_desde=fecha_inicio,
        fecha_hasta=fecha_fin,
        id_operador=id_operador,
        nombre_operador=nombre_operador,
    )


@router.get("/trailers", response_model=KpiTrailersResponse)
def list_kpis_trailers(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_trailer: int | None = Query(default=None),
    numero_economico: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_kpis_trailers(
        db,
        fecha_desde=fecha_inicio,
        fecha_hasta=fecha_fin,
        id_trailer=id_trailer,
        numero_economico=numero_economico,
    )


@router.get("/clientes", response_model=KpiClientesResponse)
def list_kpis_clientes(
    fecha_inicio: date | None = Query(default=None),
    fecha_fin: date | None = Query(default=None),
    id_cliente: int | None = Query(default=None),
    nombre_cliente: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return get_kpis_clientes(
        db,
        fecha_desde=fecha_inicio,
        fecha_hasta=fecha_fin,
        id_cliente=id_cliente,
        nombre_cliente=nombre_cliente,
    )
