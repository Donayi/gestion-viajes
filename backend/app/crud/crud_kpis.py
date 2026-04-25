from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.models import EventoOperativoViaje, Operador, Viaje
from app.schemas.kpi_operativo import (
    KpiOperativoDashboardResponse,
    KpiOperativoFilterParams,
    KpiOperativoResumenResponse,
    KpiOperativoViajeRowResponse,
)


def get_kpis_operativos_dashboard(
    db: Session,
    filters: KpiOperativoFilterParams,
) -> KpiOperativoDashboardResponse:
    viajes = _get_viajes_con_eventos_filtrados(db, filters)
    if not viajes:
        return KpiOperativoDashboardResponse(
            resumen=KpiOperativoResumenResponse(
                total_viajes_con_eventos=0,
                km_total_recorridos=0.0,
                km_promedio_por_viaje=0.0,
                diesel_total_consumido_estimado=0.0,
                diesel_promedio_consumido=0.0,
                numero_total_standbys=0,
                viajes_finalizados_con_kpi=0,
            ),
            viajes=[],
        )

    eventos = _get_eventos_operativos_filtrados(
        db,
        [viaje.id_viaje for viaje in viajes],
        filters,
    )
    eventos_por_viaje = defaultdict(list)
    for evento in eventos:
        eventos_por_viaje[evento.id_viaje].append(evento)

    operadores = _get_operadores_map(db, eventos)
    rows = [
        _build_kpi_row(viaje, eventos_por_viaje.get(viaje.id_viaje, []), operadores)
        for viaje in viajes
    ]

    if filters.solo_completos:
        rows = [row for row in rows if row.kpi_completo]

    resumen = _calcular_resumen_kpis(rows)
    return KpiOperativoDashboardResponse(resumen=resumen, viajes=rows)


def _get_viajes_con_eventos_filtrados(
    db: Session,
    filters: KpiOperativoFilterParams,
) -> list[Viaje]:
    query = (
        db.query(Viaje)
        .join(EventoOperativoViaje, EventoOperativoViaje.id_viaje == Viaje.id_viaje)
        .options(joinedload(Viaje.cliente), joinedload(Viaje.operador_actual))
    )

    start_dt, end_dt = _resolve_date_range(filters.fecha_desde, filters.fecha_hasta)
    if start_dt is not None:
        query = query.filter(EventoOperativoViaje.created_at >= start_dt)
    if end_dt is not None:
        query = query.filter(EventoOperativoViaje.created_at <= end_dt)

    if filters.id_operador is not None:
        query = query.filter(EventoOperativoViaje.id_operador == filters.id_operador)
    if filters.id_cliente is not None:
        query = query.filter(Viaje.id_cliente == filters.id_cliente)
    if filters.id_estatus is not None:
        query = query.filter(Viaje.id_estatus_actual == filters.id_estatus)

    return query.distinct().order_by(Viaje.id_viaje.desc()).all()


def _get_eventos_operativos_filtrados(
    db: Session,
    viaje_ids: list[int],
    filters: KpiOperativoFilterParams,
) -> list[EventoOperativoViaje]:
    if not viaje_ids:
        return []

    query = db.query(EventoOperativoViaje).filter(EventoOperativoViaje.id_viaje.in_(viaje_ids))

    start_dt, end_dt = _resolve_date_range(filters.fecha_desde, filters.fecha_hasta)
    if start_dt is not None:
        query = query.filter(EventoOperativoViaje.created_at >= start_dt)
    if end_dt is not None:
        query = query.filter(EventoOperativoViaje.created_at <= end_dt)

    if filters.id_operador is not None:
        query = query.filter(EventoOperativoViaje.id_operador == filters.id_operador)

    return (
        query.order_by(EventoOperativoViaje.created_at.asc(), EventoOperativoViaje.id_evento.asc()).all()
    )


def _get_operadores_map(
    db: Session,
    eventos: list[EventoOperativoViaje],
) -> dict[int, str]:
    operator_ids = {evento.id_operador for evento in eventos if evento.id_operador is not None}
    if not operator_ids:
        return {}

    operadores = db.query(Operador).filter(Operador.id_operador.in_(operator_ids)).all()
    return {operador.id_operador: operador.alias for operador in operadores}


def _build_kpi_row(
    viaje: Viaje,
    eventos: list[EventoOperativoViaje],
    operadores: dict[int, str],
) -> KpiOperativoViajeRowResponse:
    inicio_evento = next((evento for evento in eventos if evento.tipo_evento == "INICIO_VIAJE"), None)
    final_evento = next(
        (evento for evento in reversed(eventos) if evento.tipo_evento == "FINALIZACION_VIAJE"),
        None,
    )
    numero_standbys = sum(1 for evento in eventos if evento.tipo_evento == "STANDBY")

    km_inicio = _decimal_to_float(inicio_evento.kilometraje) if inicio_evento else None
    km_final = _decimal_to_float(final_evento.kilometraje) if final_evento else None
    diesel_inicio = _decimal_to_float(inicio_evento.nivel_diesel) if inicio_evento else None
    diesel_final = _decimal_to_float(final_evento.nivel_diesel) if final_evento else None

    kpi_completo = inicio_evento is not None and final_evento is not None

    km_recorridos = None
    if km_inicio is not None and km_final is not None and km_final >= km_inicio:
        km_recorridos = round(km_final - km_inicio, 2)

    diesel_consumido = None
    if (
        diesel_inicio is not None
        and diesel_final is not None
        and diesel_final <= diesel_inicio
    ):
        diesel_consumido = round(diesel_inicio - diesel_final, 2)

    anomalia = _resolver_anomalia(inicio_evento, final_evento, km_inicio, km_final, diesel_inicio, diesel_final)
    kpi_valido = kpi_completo and anomalia is None

    operador_id = (
        inicio_evento.id_operador
        if inicio_evento and inicio_evento.id_operador is not None
        else final_evento.id_operador if final_evento and final_evento.id_operador is not None
        else viaje.id_operador_actual
    )
    operador = operadores.get(operador_id) if operador_id is not None else viaje.operador_actual.alias if viaje.operador_actual else None

    return KpiOperativoViajeRowResponse(
        id_viaje=viaje.id_viaje,
        folio=viaje.folio,
        cliente=viaje.cliente.nombre_razon_social,
        operador=operador,
        km_inicio=km_inicio,
        km_final=km_final,
        km_recorridos=km_recorridos,
        diesel_inicio=diesel_inicio,
        diesel_final=diesel_final,
        diesel_consumido=diesel_consumido,
        numero_standbys=numero_standbys,
        ubicacion_inicio=inicio_evento.ubicacion if inicio_evento else None,
        ubicacion_final=final_evento.ubicacion if final_evento else None,
        fecha_inicio=inicio_evento.created_at if inicio_evento else None,
        fecha_finalizacion=final_evento.created_at if final_evento else None,
        kpi_completo=kpi_completo,
        kpi_valido=kpi_valido,
        anomalia=anomalia,
    )


def _resolver_anomalia(
    inicio_evento: EventoOperativoViaje | None,
    final_evento: EventoOperativoViaje | None,
    km_inicio: float | None,
    km_final: float | None,
    diesel_inicio: float | None,
    diesel_final: float | None,
) -> str | None:
    if inicio_evento is None:
        return "EVENTO_INICIO_FALTANTE"
    if final_evento is None:
        return "EVENTO_FINAL_FALTANTE"
    if km_inicio is not None and km_final is not None and km_final < km_inicio:
        return "KM_FINAL_MENOR_INICIO"
    if diesel_inicio is not None and diesel_final is not None and diesel_final > diesel_inicio:
        return "DIESEL_FINAL_MAYOR_INICIO"
    return None


def _calcular_resumen_kpis(rows: list[KpiOperativoViajeRowResponse]) -> KpiOperativoResumenResponse:
    km_values = [row.km_recorridos for row in rows if row.km_recorridos is not None]
    diesel_values = [row.diesel_consumido for row in rows if row.diesel_consumido is not None]

    km_total = round(sum(km_values), 2) if km_values else 0.0
    diesel_total = round(sum(diesel_values), 2) if diesel_values else 0.0

    return KpiOperativoResumenResponse(
        total_viajes_con_eventos=len(rows),
        km_total_recorridos=km_total,
        km_promedio_por_viaje=round(km_total / len(km_values), 2) if km_values else 0.0,
        diesel_total_consumido_estimado=diesel_total,
        diesel_promedio_consumido=round(diesel_total / len(diesel_values), 2) if diesel_values else 0.0,
        numero_total_standbys=sum(row.numero_standbys for row in rows),
        viajes_finalizados_con_kpi=sum(1 for row in rows if row.kpi_completo and row.kpi_valido),
    )


def _resolve_date_range(
    fecha_desde: date | None,
    fecha_hasta: date | None,
) -> tuple[datetime | None, datetime | None]:
    start_dt = datetime.combine(fecha_desde, time.min) if fecha_desde else None
    end_dt = datetime.combine(fecha_hasta, time.max) if fecha_hasta else None
    return start_dt, end_dt


def _decimal_to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)
