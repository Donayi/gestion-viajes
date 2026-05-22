from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.models import (
    AsignacionViaje,
    CatalogoEstatusViaje,
    Cliente,
    EventoOperativoViaje,
    HistorialEstatusViaje,
    Operador,
    Trailer,
    Usuario,
    Viaje,
)
from app.schemas.kpi_catalogado import (
    KpiClienteItemResponse,
    KpiClientesResponse,
    KpiOperadorItemResponse,
    KpiOperadoresResponse,
    KpiPeriodoResponse,
    KpiSerieItemResponse,
    KpiTrailerItemResponse,
    KpiTrailerViajeDetalleResponse,
    KpiTrailersResponse,
)
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
    eventos_kpi = [
        evento
        for evento in eventos
        if evento.tipo_evento in {"INICIO_VIAJE", "STANDBY", "FINALIZACION_VIAJE"}
    ]

    inicio_evento = next((evento for evento in eventos_kpi if evento.tipo_evento == "INICIO_VIAJE"), None)
    final_evento = next(
        (evento for evento in reversed(eventos_kpi) if evento.tipo_evento == "FINALIZACION_VIAJE"),
        None,
    )
    numero_standbys = sum(1 for evento in eventos_kpi if evento.tipo_evento == "STANDBY")

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


def get_kpis_operadores(
    db: Session,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    id_operador: int | None = None,
    nombre_operador: str | None = None,
) -> KpiOperadoresResponse:
    start_dt, end_dt = _resolve_date_range(fecha_desde, fecha_hasta)
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = datetime.combine(week_start, time.min)
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, time.min)

    operadores_query = db.query(Operador).options(joinedload(Operador.usuario))
    if id_operador is not None:
        operadores_query = operadores_query.filter(Operador.id_operador == id_operador)
    if nombre_operador:
        search = f"%{nombre_operador.strip()}%"
        operadores_query = (
            operadores_query.join(Operador.usuario)
            .filter(
                or_(
                    Operador.alias.ilike(search),
                    Usuario.nombre.ilike(search),
                    Usuario.apellido.ilike(search),
                    (Usuario.nombre + " " + Usuario.apellido).ilike(search),
                )
            )
        )
    operadores = operadores_query.all()
    operadores_map = {
        operador.id_operador: {
            "nombre_operador": operador.alias,
            "nombre_completo": (
                f"{operador.usuario.nombre} {operador.usuario.apellido}".strip()
                if operador.usuario
                else None
            ),
        }
        for operador in operadores
    }
    operador_ids = list(operadores_map.keys())

    eventos_query = db.query(EventoOperativoViaje).filter(EventoOperativoViaje.id_operador.is_not(None))
    if start_dt is not None:
        eventos_query = eventos_query.filter(EventoOperativoViaje.created_at >= start_dt)
    if end_dt is not None:
        eventos_query = eventos_query.filter(EventoOperativoViaje.created_at <= end_dt)
    if id_operador is not None:
        eventos_query = eventos_query.filter(EventoOperativoViaje.id_operador == id_operador)
    elif operador_ids:
        eventos_query = eventos_query.filter(EventoOperativoViaje.id_operador.in_(operador_ids))
    elif nombre_operador:
        eventos_query = eventos_query.filter(False)
    eventos = eventos_query.order_by(
        EventoOperativoViaje.created_at.asc(),
        EventoOperativoViaje.id_evento.asc(),
    ).all()

    assignments_query = db.query(AsignacionViaje).filter(AsignacionViaje.id_operador.is_not(None))
    if start_dt is not None:
        assignments_query = assignments_query.filter(AsignacionViaje.fecha_asignacion >= start_dt)
    if end_dt is not None:
        assignments_query = assignments_query.filter(AsignacionViaje.fecha_asignacion <= end_dt)
    if id_operador is not None:
        assignments_query = assignments_query.filter(AsignacionViaje.id_operador == id_operador)
    elif operador_ids:
        assignments_query = assignments_query.filter(AsignacionViaje.id_operador.in_(operador_ids))
    elif nombre_operador:
        assignments_query = assignments_query.filter(False)
    assignments = assignments_query.all()

    viajes_semana_por_operador: dict[int, set[int]] = defaultdict(set)
    viajes_mes_por_operador: dict[int, set[int]] = defaultdict(set)
    viajes_registrados_por_operador: set[tuple[int, int]] = set()

    for evento in eventos:
        if evento.id_operador is None:
            continue
        pair = (evento.id_operador, evento.id_viaje)
        viajes_registrados_por_operador.add(pair)
        if evento.created_at >= week_start_dt:
            viajes_semana_por_operador[evento.id_operador].add(evento.id_viaje)
        if evento.created_at >= month_start_dt:
            viajes_mes_por_operador[evento.id_operador].add(evento.id_viaje)

    for asignacion in assignments:
        if asignacion.id_operador is None:
            continue
        pair = (asignacion.id_operador, asignacion.id_viaje)
        if pair in viajes_registrados_por_operador:
            continue
        if asignacion.fecha_asignacion >= week_start_dt:
            viajes_semana_por_operador[asignacion.id_operador].add(asignacion.id_viaje)
        if asignacion.fecha_asignacion >= month_start_dt:
            viajes_mes_por_operador[asignacion.id_operador].add(asignacion.id_viaje)

    km_por_segmento: dict[tuple[int, int, int], list[float]] = defaultdict(list)
    for evento in eventos:
        if evento.id_operador is None or evento.id_trailer is None or evento.kilometraje is None:
            continue
        key = (evento.id_operador, evento.id_viaje, evento.id_trailer)
        km_por_segmento[key].append(float(evento.kilometraje))

    km_por_operador: dict[int, float] = defaultdict(float)
    for (operador_segmento, _, _), kilometrajes in km_por_segmento.items():
        if len(kilometrajes) < 2:
            continue
        km_por_operador[operador_segmento] += max(kilometrajes) - min(kilometrajes)

    operadores_rows = [
        KpiOperadorItemResponse(
            id_operador=operador.id_operador,
            nombre=operadores_map.get(operador.id_operador, {}).get("nombre_completo") or operador.alias,
            nombre_operador=operadores_map.get(operador.id_operador, {}).get("nombre_operador") or operador.alias,
            nombre_completo=operadores_map.get(operador.id_operador, {}).get("nombre_completo"),
            viajes_semana=len(viajes_semana_por_operador.get(operador.id_operador, set())),
            viajes_mes=len(viajes_mes_por_operador.get(operador.id_operador, set())),
            km_recorridos=round(km_por_operador.get(operador.id_operador, 0.0), 2),
      )
      for operador in operadores
    ]

    series_semanales = _build_weekly_series_from_timestamps(
      [evento.created_at for evento in eventos if evento.id_operador is not None],
      start_dt,
      end_dt,
    )
    series_mensuales = _build_monthly_series_from_timestamps(
      [evento.created_at for evento in eventos if evento.id_operador is not None],
      start_dt,
      end_dt,
    )

    return KpiOperadoresResponse(
        periodo=KpiPeriodoResponse(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta),
        total_viajes_semana=sum(row.viajes_semana for row in operadores_rows),
        total_viajes_mes=sum(row.viajes_mes for row in operadores_rows),
        total_km_recorridos=round(sum(row.km_recorridos for row in operadores_rows), 2),
        series_semanales=series_semanales,
        series_mensuales=series_mensuales,
        operadores=operadores_rows,
    )


def get_kpis_trailers(
    db: Session,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    id_trailer: int | None = None,
    numero_economico: str | None = None,
) -> KpiTrailersResponse:
    start_dt, end_dt = _resolve_date_range(fecha_desde, fecha_hasta)
    trailers_query = db.query(Trailer)
    if id_trailer is not None:
        trailers_query = trailers_query.filter(Trailer.id_trailer == id_trailer)
    if numero_economico:
        trailers_query = trailers_query.filter(Trailer.numero_economico.ilike(f"%{numero_economico.strip()}%"))
    trailers = trailers_query.all()
    trailer_ids = [trailer.id_trailer for trailer in trailers]
    trailers_map = {trailer.id_trailer: trailer for trailer in trailers}

    eventos_query = (
        db.query(EventoOperativoViaje, Viaje.folio)
        .join(Viaje, Viaje.id_viaje == EventoOperativoViaje.id_viaje)
        .filter(EventoOperativoViaje.id_trailer.is_not(None))
    )
    if start_dt is not None:
        eventos_query = eventos_query.filter(EventoOperativoViaje.created_at >= start_dt)
    if end_dt is not None:
        eventos_query = eventos_query.filter(EventoOperativoViaje.created_at <= end_dt)
    if id_trailer is not None:
        eventos_query = eventos_query.filter(EventoOperativoViaje.id_trailer == id_trailer)
    elif trailer_ids:
        eventos_query = eventos_query.filter(EventoOperativoViaje.id_trailer.in_(trailer_ids))
    elif numero_economico:
        eventos_query = eventos_query.filter(False)
    eventos_rows = eventos_query.order_by(
        EventoOperativoViaje.created_at.asc(),
        EventoOperativoViaje.id_evento.asc(),
    ).all()
    eventos_por_segmento: dict[tuple[int, int], list[tuple[EventoOperativoViaje, str]]] = defaultdict(list)
    for evento, folio in eventos_rows:
        if evento.id_trailer is None:
            continue
        eventos_por_segmento[(evento.id_viaje, evento.id_trailer)].append((evento, folio))

    detalles_por_trailer: dict[int, list[KpiTrailerViajeDetalleResponse]] = defaultdict(list)
    for (viaje_id, trailer_id), eventos_segmento in eventos_por_segmento.items():
        folio = eventos_segmento[0][1]
        eventos_ordenados = [row[0] for row in eventos_segmento]
        kilometrajes = [float(evento.kilometraje) for evento in eventos_ordenados if evento.kilometraje is not None]
        diesel_eventos = [evento for evento in eventos_ordenados if evento.nivel_diesel is not None]

        km_recorridos = None
        if len(kilometrajes) >= 2:
            km_recorridos = round(max(kilometrajes) - min(kilometrajes), 2)

        diesel_consumido_pct = None
        rendimiento = None
        consumo_valido = False
        if len(diesel_eventos) >= 2:
            primer_diesel = float(diesel_eventos[0].nivel_diesel)
            ultimo_diesel = float(diesel_eventos[-1].nivel_diesel)
            diesel_delta = round(primer_diesel - ultimo_diesel, 2)
            if diesel_delta > 0:
                diesel_consumido_pct = diesel_delta
                consumo_valido = True
                if km_recorridos is not None:
                    rendimiento = round(km_recorridos / diesel_delta, 2)

        detalles_por_trailer[trailer_id].append(
            KpiTrailerViajeDetalleResponse(
                id_viaje=viaje_id,
                folio=folio,
                id_trailer=trailer_id,
                numero_economico=trailers_map.get(trailer_id).numero_economico if trailer_id in trailers_map else str(trailer_id),
                km_recorridos=km_recorridos,
                diesel_consumido_pct=diesel_consumido_pct,
                rendimiento_km_por_pct_diesel=rendimiento,
                consumo_valido=consumo_valido,
            )
        )

    trailer_rows: list[KpiTrailerItemResponse] = []
    for trailer in trailers:
        detalles = detalles_por_trailer.get(trailer.id_trailer, [])
        km_total = round(sum(detalle.km_recorridos or 0 for detalle in detalles), 2)
        diesel_total = round(sum(detalle.diesel_consumido_pct or 0 for detalle in detalles), 2)
        rendimiento_total = round(km_total / diesel_total, 2) if diesel_total > 0 else None
        trailer_rows.append(
            KpiTrailerItemResponse(
                id_trailer=trailer.id_trailer,
                numero_economico=trailer.numero_economico,
                placas=trailer.placas,
                km_recorridos=km_total,
                diesel_consumido_pct=diesel_total,
                rendimiento_km_por_pct_diesel=rendimiento_total,
                viajes=detalles,
            )
        )

    total_km = round(sum(item.km_recorridos for item in trailer_rows), 2)
    total_diesel = round(sum(item.diesel_consumido_pct for item in trailer_rows), 2)

    return KpiTrailersResponse(
        periodo=KpiPeriodoResponse(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta),
        total_km_recorridos=total_km,
        total_diesel_consumido_pct=total_diesel,
        rendimiento_promedio_km_por_pct_diesel=round(total_km / total_diesel, 2) if total_diesel > 0 else None,
        trailers=trailer_rows,
    )


def get_kpis_clientes(
    db: Session,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    id_cliente: int | None = None,
    nombre_cliente: str | None = None,
) -> KpiClientesResponse:
    start_dt, end_dt = _resolve_date_range(fecha_desde, fecha_hasta)
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = datetime.combine(week_start, time.min)
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, time.min)

    clientes_query = db.query(Cliente)
    if id_cliente is not None:
        clientes_query = clientes_query.filter(Cliente.id_cliente == id_cliente)
    if nombre_cliente:
        clientes_query = clientes_query.filter(Cliente.nombre_razon_social.ilike(f"%{nombre_cliente.strip()}%"))
    clientes = clientes_query.all()
    clientes_map = {cliente.id_cliente: cliente for cliente in clientes}
    cliente_ids = list(clientes_map.keys())

    finalizados_query = (
        db.query(HistorialEstatusViaje, Viaje.id_cliente)
        .join(CatalogoEstatusViaje, HistorialEstatusViaje.id_estatus == CatalogoEstatusViaje.id_estatus)
        .join(Viaje, Viaje.id_viaje == HistorialEstatusViaje.id_viaje)
        .filter(CatalogoEstatusViaje.clave == "FINALIZADO")
    )
    if cliente_ids:
        finalizados_query = finalizados_query.filter(Viaje.id_cliente.in_(cliente_ids))
    if start_dt is not None:
        finalizados_query = finalizados_query.filter(HistorialEstatusViaje.changed_at >= start_dt)
    if end_dt is not None:
        finalizados_query = finalizados_query.filter(HistorialEstatusViaje.changed_at <= end_dt)
    finalizados = finalizados_query.all()

    viajes_espera_query = (
        db.query(Viaje)
        .join(CatalogoEstatusViaje, Viaje.id_estatus_actual == CatalogoEstatusViaje.id_estatus)
        .filter(CatalogoEstatusViaje.clave.in_(["CREADO", "ASIGNADO", "CARGANDO", "STANDBY"]))
    )
    if cliente_ids:
        viajes_espera_query = viajes_espera_query.filter(Viaje.id_cliente.in_(cliente_ids))
    if start_dt is not None:
        viajes_espera_query = viajes_espera_query.filter(Viaje.created_at >= start_dt)
    if end_dt is not None:
        viajes_espera_query = viajes_espera_query.filter(Viaje.created_at <= end_dt)
    viajes_espera = viajes_espera_query.all()

    finalizados_semana_por_cliente: dict[int, int] = defaultdict(int)
    finalizados_mes_por_cliente: dict[int, int] = defaultdict(int)
    finalizados_timestamps: list[datetime] = []
    for historial, cliente_id_row in finalizados:
        finalizados_timestamps.append(historial.changed_at)
        if historial.changed_at >= week_start_dt:
            finalizados_semana_por_cliente[cliente_id_row] += 1
        if historial.changed_at >= month_start_dt:
            finalizados_mes_por_cliente[cliente_id_row] += 1

    espera_por_cliente: dict[int, int] = defaultdict(int)
    for viaje in viajes_espera:
        espera_por_cliente[viaje.id_cliente] += 1

    cliente_rows = [
      KpiClienteItemResponse(
        id_cliente=cliente.id_cliente,
        nombre=cliente.nombre_razon_social,
        nombre_razon_social=cliente.nombre_razon_social,
        viajes_terminados_semana=finalizados_semana_por_cliente.get(cliente.id_cliente, 0),
        viajes_terminados_mes=finalizados_mes_por_cliente.get(cliente.id_cliente, 0),
        viajes_en_espera=espera_por_cliente.get(cliente.id_cliente, 0),
      )
      for cliente in clientes
    ]

    return KpiClientesResponse(
        periodo=KpiPeriodoResponse(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta),
        total_viajes_terminados_semana=sum(row.viajes_terminados_semana for row in cliente_rows),
        total_viajes_terminados_mes=sum(row.viajes_terminados_mes for row in cliente_rows),
        total_viajes_en_espera=sum(row.viajes_en_espera for row in cliente_rows),
        series_semanales=_build_weekly_series_from_timestamps(finalizados_timestamps, start_dt, end_dt),
        series_mensuales=_build_monthly_series_from_timestamps(finalizados_timestamps, start_dt, end_dt),
        clientes=cliente_rows,
    )


def _build_weekly_series_from_timestamps(
    timestamps: list[datetime],
    start_dt: datetime | None,
    end_dt: datetime | None,
) -> list[KpiSerieItemResponse]:
    if not timestamps:
        return []

    min_date = (start_dt.date() if start_dt else min(ts.date() for ts in timestamps))
    max_date = (end_dt.date() if end_dt else max(ts.date() for ts in timestamps))
    current = min_date - timedelta(days=min_date.weekday())
    final = max_date - timedelta(days=max_date.weekday())
    counts: dict[str, float] = defaultdict(float)

    for timestamp in timestamps:
        week = timestamp.date() - timedelta(days=timestamp.date().weekday())
        counts[week.isoformat()] += 1

    series: list[KpiSerieItemResponse] = []
    while current <= final:
        key = current.isoformat()
        series.append(KpiSerieItemResponse(etiqueta=key, valor=counts.get(key, 0.0)))
        current += timedelta(days=7)
    return series


def _build_monthly_series_from_timestamps(
    timestamps: list[datetime],
    start_dt: datetime | None,
    end_dt: datetime | None,
) -> list[KpiSerieItemResponse]:
    if not timestamps:
        return []

    min_date = start_dt.date() if start_dt else min(ts.date() for ts in timestamps)
    max_date = end_dt.date() if end_dt else max(ts.date() for ts in timestamps)
    current_year = min_date.year
    current_month = min_date.month
    final_year = max_date.year
    final_month = max_date.month
    counts: dict[str, float] = defaultdict(float)

    for timestamp in timestamps:
        key = f"{timestamp.year:04d}-{timestamp.month:02d}"
        counts[key] += 1

    series: list[KpiSerieItemResponse] = []
    while (current_year, current_month) <= (final_year, final_month):
        key = f"{current_year:04d}-{current_month:02d}"
        series.append(KpiSerieItemResponse(etiqueta=key, valor=counts.get(key, 0.0)))
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    return series
