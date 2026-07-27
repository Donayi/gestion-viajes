from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.crud.crud_kpis import get_kpis_operativos_dashboard
from app.crud.crud_viajes import get_disponibilidad_resumen, get_viajes_mapa
from app.models.models import Alerta, CatalogoEstatusViaje, Mantenimiento, Viaje
from app.schemas.dashboard import (
    AdminDashboardResponse,
    DashboardAlertasResumenResponse,
    DashboardAlertaItemResponse,
    DashboardDisponibilidadCajasResponse,
    DashboardDisponibilidadGrupoResponse,
    DashboardDisponibilidadResponse,
    DashboardDisponibilidadTrailersResponse,
    DashboardMapaResumenResponse,
    DashboardMantenimientosResumenResponse,
    DashboardMantenimientoEntidadResponse,
    DashboardMantenimientoItemResponse,
    DashboardStatusCountResponse,
    DashboardViajesResumenResponse,
)
from app.schemas.kpi_operativo import KpiOperativoFilterParams, KpiOperativoResumenResponse


ALERT_ITEMS_LIMIT = 5
MANTENIMIENTO_ITEMS_LIMIT = 5
MAPA_ITEMS_LIMIT = 50
MANTENIMIENTO_SOON_DAYS = 3
MANTENIMIENTO_ACTIVOS = ("ABIERTO", "EN_PROCESO")


def get_admin_dashboard(db: Session) -> AdminDashboardResponse:
    """Agrega el dashboard reutilizando funciones existentes de viajes y KPIs.

    Reutiliza:
    - get_kpis_operativos_dashboard para el resumen operativo.
    - get_disponibilidad_resumen para las reglas actuales de disponibilidad.
    - get_viajes_mapa para la vista resumida del mapa operativo.
    """

    mapa_items = get_viajes_mapa(
        db,
        estatus_claves=None,
        incluir_finalizados=True,
        incluir_cancelados=True,
    )
    mapa = _build_mapa_payload(mapa_items)
    viajes_resumen = _get_viajes_resumen(db, mapa.total_sin_ubicacion)

    return AdminDashboardResponse(
        generated_at=datetime.now(timezone.utc),
        viajes_resumen=viajes_resumen,
        kpis_operativos=_get_kpis_operativos_resumen(db),
        disponibilidad=_get_disponibilidad_payload(db),
        alertas=_get_alertas_payload(db),
        mantenimientos=_get_mantenimientos_payload(db),
        mapa=mapa,
    )


def _get_kpis_operativos_resumen(db: Session) -> KpiOperativoResumenResponse:
    return get_kpis_operativos_dashboard(db, KpiOperativoFilterParams()).resumen


def _get_viajes_resumen(
    db: Session,
    total_sin_ubicacion: int,
) -> DashboardViajesResumenResponse:
    rows = (
        db.query(
            CatalogoEstatusViaje.clave,
            CatalogoEstatusViaje.nombre,
            CatalogoEstatusViaje.es_terminal,
            func.count(Viaje.id_viaje).label("total"),
        )
        .outerjoin(Viaje, Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus)
        .filter(CatalogoEstatusViaje.activo.is_(True))
        .group_by(
            CatalogoEstatusViaje.id_estatus,
            CatalogoEstatusViaje.clave,
            CatalogoEstatusViaje.nombre,
            CatalogoEstatusViaje.es_terminal,
            CatalogoEstatusViaje.orden_flujo,
        )
        .order_by(
            CatalogoEstatusViaje.orden_flujo.asc().nullslast(),
            CatalogoEstatusViaje.id_estatus.asc(),
        )
        .all()
    )

    por_estatus = [
        DashboardStatusCountResponse(
            clave=row.clave,
            nombre=row.nombre,
            total=int(row.total or 0),
        )
        for row in rows
    ]
    counts = {row.clave: int(row.total or 0) for row in rows}
    total = sum(counts.values())
    activos = sum(int(row.total or 0) for row in rows if not row.es_terminal)

    return DashboardViajesResumenResponse(
        total=total,
        activos=activos,
        finalizados=counts.get("FINALIZADO", 0),
        standby=counts.get("STANDBY", 0),
        cancelados=counts.get("CANCELADO", 0),
        sin_ubicacion=total_sin_ubicacion,
        por_estatus=por_estatus,
    )


def _get_disponibilidad_payload(db: Session) -> DashboardDisponibilidadResponse:
    summary = get_disponibilidad_resumen(db)
    operadores = summary.get("operadores", [])
    trailers = summary.get("trailers", [])
    cajas = summary.get("cajas", [])

    operadores_total = len(operadores)
    operadores_disponibles = sum(1 for item in operadores if item.get("disponible"))
    operadores_inactivos = sum(1 for item in operadores if not item.get("activo"))

    trailers_total = len(trailers)
    trailers_disponibles = sum(1 for item in trailers if item.get("disponible"))
    trailers_inactivos = sum(1 for item in trailers if not item.get("activo"))
    trailers_mantenimiento = sum(
        1 for item in trailers if item.get("motivo_no_disponible") == "En mantenimiento"
    )

    cajas_total = len(cajas)
    cajas_disponibles = sum(1 for item in cajas if item.get("disponible"))
    cajas_inactivas = sum(1 for item in cajas if not item.get("activo"))
    cajas_mantenimiento = sum(
        1 for item in cajas if item.get("motivo_no_disponible") == "En mantenimiento"
    )

    return DashboardDisponibilidadResponse(
        operadores=DashboardDisponibilidadGrupoResponse(
            total=operadores_total,
            disponibles=operadores_disponibles,
            ocupados=max(operadores_total - operadores_disponibles - operadores_inactivos, 0),
            inactivos=operadores_inactivos,
        ),
        trailers=DashboardDisponibilidadTrailersResponse(
            total=trailers_total,
            disponibles=trailers_disponibles,
            ocupados=max(
                trailers_total - trailers_disponibles - trailers_inactivos - trailers_mantenimiento,
                0,
            ),
            en_mantenimiento=trailers_mantenimiento,
            inactivos=trailers_inactivos,
        ),
        cajas=DashboardDisponibilidadCajasResponse(
            total=cajas_total,
            disponibles=cajas_disponibles,
            ocupadas=max(cajas_total - cajas_disponibles - cajas_inactivas - cajas_mantenimiento, 0),
            en_mantenimiento=cajas_mantenimiento,
            inactivas=cajas_inactivas,
        ),
    )


def _get_alertas_payload(db: Session) -> DashboardAlertasResumenResponse:
    pending_case = case((Alerta.leida.is_(False), 1), else_=0)
    critical_pending_case = case(
        ((Alerta.leida.is_(False)) & (Alerta.nivel == "CRITICAL"), 1),
        else_=0,
    )
    counts = db.query(
        func.coalesce(func.sum(pending_case), 0).label("pendientes_total"),
        func.coalesce(func.sum(critical_pending_case), 0).label("criticas_no_leidas"),
    ).one()
    items = (
        db.query(Alerta)
        .order_by(Alerta.created_at.desc(), Alerta.id_alerta.desc())
        .limit(ALERT_ITEMS_LIMIT)
        .all()
    )

    return _build_alertas_payload(
        pendientes_total=int(counts.pendientes_total or 0),
        criticas_no_leidas=int(counts.criticas_no_leidas or 0),
        items=items,
    )


def _build_alertas_payload(
    *,
    pendientes_total: int,
    criticas_no_leidas: int,
    items: list[Alerta],
) -> DashboardAlertasResumenResponse:
    return DashboardAlertasResumenResponse(
        pendientes_total=pendientes_total,
        criticas_no_leidas=criticas_no_leidas,
        items=[
            DashboardAlertaItemResponse(
                id_alerta=item.id_alerta,
                tipo_alerta=item.tipo_alerta,
                entidad_tipo=item.entidad_tipo,
                entidad_id=item.entidad_id,
                mensaje=item.mensaje,
                nivel=item.nivel,
                leida=item.leida,
                created_at=item.created_at,
            )
            for item in items[:ALERT_ITEMS_LIMIT]
        ],
    )


def _get_mantenimientos_payload(db: Session) -> DashboardMantenimientosResumenResponse:
    today = date.today()
    soon_limit = today + timedelta(days=MANTENIMIENTO_SOON_DAYS)

    abiertos_case = case((Mantenimiento.estatus == "ABIERTO", 1), else_=0)
    en_proceso_case = case((Mantenimiento.estatus == "EN_PROCESO", 1), else_=0)
    proximos_case = case(
        (
            (Mantenimiento.estatus.in_(MANTENIMIENTO_ACTIVOS))
            & (Mantenimiento.fecha_proximo_mantenimiento.is_not(None))
            & (Mantenimiento.fecha_proximo_mantenimiento <= soon_limit),
            1,
        ),
        else_=0,
    )
    counts = db.query(
        func.coalesce(func.sum(abiertos_case), 0).label("abiertos_total"),
        func.coalesce(func.sum(en_proceso_case), 0).label("en_proceso_total"),
        func.coalesce(func.sum(proximos_case), 0).label("proximos_total"),
    ).one()

    prioridad_estatus = case(
        (Mantenimiento.estatus == "EN_PROCESO", 0),
        (Mantenimiento.estatus == "ABIERTO", 1),
        else_=2,
    )
    fecha_prioridad = func.coalesce(
        Mantenimiento.fecha_proximo_mantenimiento,
        Mantenimiento.fecha_mantenimiento,
        func.date(Mantenimiento.fecha_inicio),
    )

    items = (
        db.query(Mantenimiento)
        .options(
            joinedload(Mantenimiento.trailer),
            joinedload(Mantenimiento.caja),
        )
        .filter(Mantenimiento.estatus.in_(MANTENIMIENTO_ACTIVOS))
        .order_by(
            prioridad_estatus.asc(),
            fecha_prioridad.asc(),
            Mantenimiento.fecha_inicio.desc(),
            Mantenimiento.id_mantenimiento.desc(),
        )
        .limit(MANTENIMIENTO_ITEMS_LIMIT)
        .all()
    )

    return _build_mantenimientos_payload(
        abiertos_total=int(counts.abiertos_total or 0),
        en_proceso_total=int(counts.en_proceso_total or 0),
        proximos_total=int(counts.proximos_total or 0),
        items=items,
    )


def _build_mantenimientos_payload(
    *,
    abiertos_total: int,
    en_proceso_total: int,
    proximos_total: int,
    items: list[Mantenimiento],
) -> DashboardMantenimientosResumenResponse:
    return DashboardMantenimientosResumenResponse(
        abiertos_total=abiertos_total,
        en_proceso_total=en_proceso_total,
        proximos_total=proximos_total,
        items=[
            DashboardMantenimientoItemResponse(
                id_mantenimiento=item.id_mantenimiento,
                entidad_tipo=item.entidad_tipo,
                entidad_id=item.entidad_id,
                tipo_mantenimiento=item.tipo_mantenimiento,
                estatus=item.estatus,
                fecha_inicio=item.fecha_inicio,
                fecha_mantenimiento=item.fecha_mantenimiento,
                fecha_proximo_mantenimiento=item.fecha_proximo_mantenimiento,
                descripcion=item.descripcion,
                entidad=DashboardMantenimientoEntidadResponse(**item.entidad),
            )
            for item in items[:MANTENIMIENTO_ITEMS_LIMIT]
        ],
    )


def _build_mapa_payload(viajes_mapa: list[dict]) -> DashboardMapaResumenResponse:
    total_con_ubicacion = sum(1 for item in viajes_mapa if _mapa_item_has_location(item))
    return DashboardMapaResumenResponse(
        total_con_ubicacion=total_con_ubicacion,
        total_sin_ubicacion=max(len(viajes_mapa) - total_con_ubicacion, 0),
        items=viajes_mapa[:MAPA_ITEMS_LIMIT],
    )


def _mapa_item_has_location(item: dict) -> bool:
    ultima_ubicacion = item.get("ultima_ubicacion")
    if not isinstance(ultima_ubicacion, dict):
        return False
    return (
        ultima_ubicacion.get("latitud") is not None
        and ultima_ubicacion.get("longitud") is not None
    )
