from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.api import deps_auth, routes_viajes
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.crud_viajes import finalizar_viaje, iniciar_viaje
from app.db.deps import get_db
from app.models.models import (
    ArchivoStorage,
    AsignacionViaje,
    Caja,
    CatalogoEstatusViaje,
    Cliente,
    Evidencia,
    EventoOperativoViaje,
    HistorialEstatusViaje,
    Operador,
    Rol,
    TipoEvidencia,
    Trailer,
    TransicionEstatusViaje,
    Usuario,
    Viaje,
)
from app.schemas.evidencia import EvidenciaOperativaInput
from app.schemas.evento_operativo import EventoOperativoViajePayload
from app.schemas.viaje import ViajeCambioEstatus


TIPO_INICIO = "EVIDENCIA_INICIO"
TIPO_CIERRE = "EVIDENCIA_CIERRE"
TIPO_GENERAL = "EVIDENCIA_GENERAL"


class FakeContractDbSession:
    def __init__(self, estatus_destino):
        self.estatus_destino = estatus_destino

    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.estatus_destino

    def rollback(self):
        return None


@pytest.fixture
def escenario_evidencias(db_session):
    rol = Rol(nombre="OPERADOR", descripcion="Rol aislado de pruebas")
    usuario = Usuario(
        username="operador_evidencias_test",
        password_hash="not-used",
        nombre="Operador",
        apellido="Evidencias",
        rol=rol,
    )
    operador = Operador(alias="Operador evidencias", usuario=usuario)
    cliente = Cliente(nombre_razon_social="Cliente evidencias")
    trailer = Trailer(numero_economico="T-EVID-001", placas="TR-EVID-001")
    caja = Caja(numero_economico="C-EVID-001", placas="CJ-EVID-001")

    estados = {
        clave: CatalogoEstatusViaje(
            clave=clave,
            nombre=clave.title(),
            orden_flujo=orden,
            es_terminal=clave == "FINALIZADO",
            requiere_evidencia=clave in {"INICIADO", "FINALIZADO"},
        )
        for orden, clave in enumerate(
            ["CREADO", "ASIGNADO", "CARGANDO", "INICIADO", "RETRASADO", "FINALIZADO"],
            start=1,
        )
    }
    tipos = {
        nombre: TipoEvidencia(nombre=nombre, descripcion=f"Tipo {nombre}")
        for nombre in (TIPO_INICIO, TIPO_CIERRE, TIPO_GENERAL)
    }
    archivos = {
        nombre: ArchivoStorage(
            proveedor="LOCAL_TEST",
            bucket="test-evidencias",
            file_key=f"tests/{nombre.lower()}.jpg",
            nombre_original=f"{nombre.lower()}.jpg",
            content_type="image/jpeg",
        )
        for nombre in (TIPO_INICIO, TIPO_CIERRE, TIPO_GENERAL)
    }

    db_session.add_all(
        [rol, usuario, operador, cliente, trailer, caja, *estados.values(), *tipos.values(), *archivos.values()]
    )
    db_session.flush()

    transiciones = [
        TransicionEstatusViaje(
            id_estatus_origen=estados[origen].id_estatus,
            id_estatus_destino=estados[destino].id_estatus,
            requiere_comentario=requiere_comentario,
            requiere_evidencia=destino in {"INICIADO", "FINALIZADO"},
        )
        for origen, destino, requiere_comentario in (
            ("CREADO", "ASIGNADO", False),
            ("CARGANDO", "INICIADO", False),
            ("INICIADO", "RETRASADO", True),
            ("INICIADO", "FINALIZADO", False),
            ("RETRASADO", "FINALIZADO", True),
        )
    ]
    db_session.add_all(transiciones)

    viaje = Viaje(
        folio="VIAJE-EVIDENCIAS-001",
        id_cliente=cliente.id_cliente,
        lugar_inicio="Origen evidencias",
        lugar_destino="Destino evidencias",
        id_estatus_actual=estados["CARGANDO"].id_estatus,
        id_operador_actual=operador.id_operador,
        id_trailer_actual=trailer.id_trailer,
        id_caja_actual=caja.id_caja,
    )
    db_session.add(viaje)
    db_session.flush()

    asignacion = AsignacionViaje(
        id_viaje=viaje.id_viaje,
        id_operador=operador.id_operador,
        id_trailer=trailer.id_trailer,
        id_caja=caja.id_caja,
        activo=True,
    )
    historial_inicial = HistorialEstatusViaje(
        id_viaje=viaje.id_viaje,
        id_estatus=estados["CARGANDO"].id_estatus,
        comentario="Escenario inicial",
    )
    db_session.add_all([asignacion, historial_inicial])
    db_session.commit()

    return {
        "usuario": usuario,
        "operador": operador,
        "trailer": trailer,
        "caja": caja,
        "viaje": viaje,
        "asignacion": asignacion,
        "estados": estados,
        "tipos": tipos,
        "archivos": archivos,
        "historial_inicial": historial_inicial,
    }


def _evidencia_input(escenario, nombre_tipo):
    return EvidenciaOperativaInput(
        id_tipo_evidencia=escenario["tipos"][nombre_tipo].id_tipo_evidencia,
        id_archivo=escenario["archivos"][nombre_tipo].id_archivo,
        comentario=f"Captura {nombre_tipo}",
        latitud=25.45,
        longitud=-100.99,
    )


def _payload(evidencias, *, kilometraje=1000):
    return EventoOperativoViajePayload(
        ubicacion="Ubicación de prueba",
        latitud=25.45,
        longitud=-100.99,
        comentario="Acción con evidencias",
        kilometraje=kilometraje,
        nivel_diesel=75,
        evidencias=evidencias,
    )


def _auth_headers(usuario):
    token = create_access_token(
        {
            "sub": str(usuario.id_usuario),
            "username": usuario.username,
            "role": usuario.rol.nombre,
            "operator_id": usuario.operador.id_operador,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _preparar_finalizacion(db_session, escenario):
    viaje = escenario["viaje"]
    viaje.id_estatus_actual = escenario["estados"]["INICIADO"].id_estatus
    viaje.id_operador_actual = escenario["operador"].id_operador
    viaje.id_trailer_actual = escenario["trailer"].id_trailer
    viaje.id_caja_actual = escenario["caja"].id_caja
    escenario["asignacion"].activo = True
    escenario["asignacion"].fecha_fin_asignacion = None
    db_session.add(
        HistorialEstatusViaje(
            id_viaje=viaje.id_viaje,
            id_estatus=escenario["estados"]["INICIADO"].id_estatus,
            comentario="Viaje iniciado antes de finalizar",
        )
    )
    db_session.commit()


def _snapshot_atomico(db_session, viaje_id):
    db_session.expire_all()
    viaje = db_session.get(Viaje, viaje_id)
    asignacion = db_session.query(AsignacionViaje).filter_by(id_viaje=viaje_id).one()
    return {
        "eventos": db_session.query(EventoOperativoViaje).filter_by(id_viaje=viaje_id).count(),
        "evidencias": db_session.query(Evidencia).filter_by(id_viaje=viaje_id).count(),
        "historial": db_session.query(HistorialEstatusViaje).filter_by(id_viaje=viaje_id).count(),
        "id_estatus_actual": viaje.id_estatus_actual,
        "fecha_inicio": viaje.fecha_inicio,
        "fecha_llegada": viaje.fecha_llegada,
        "id_operador_actual": viaje.id_operador_actual,
        "id_trailer_actual": viaje.id_trailer_actual,
        "id_caja_actual": viaje.id_caja_actual,
        "asignacion_activa": asignacion.activo,
        "fecha_inicio_operacion": asignacion.fecha_inicio_operacion,
        "fecha_fin_asignacion": asignacion.fecha_fin_asignacion,
    }


@contextmanager
def _strict_evidence_validation(enabled):
    original = settings.strict_evidence_validation
    settings.strict_evidence_validation = enabled
    try:
        yield
    finally:
        settings.strict_evidence_validation = original


@pytest.mark.parametrize(
    "tipos_payload",
    [
        [TIPO_INICIO],
        [TIPO_INICIO, TIPO_INICIO],
        [TIPO_INICIO, TIPO_GENERAL],
        [TIPO_GENERAL, TIPO_INICIO, TIPO_GENERAL],
    ],
)
def test_inicio_acepta_matriz_permitida(db_session, escenario_evidencias, tipos_payload):
    viaje = escenario_evidencias["viaje"]
    payload = _payload([_evidencia_input(escenario_evidencias, tipo) for tipo in tipos_payload])

    iniciar_viaje(db_session, viaje, payload)

    db_session.expire_all()
    persistido = db_session.get(Viaje, viaje.id_viaje)
    evidencias = db_session.query(Evidencia).filter_by(id_viaje=viaje.id_viaje).all()
    assert persistido.estatus_actual.clave == "INICIADO"
    assert len(evidencias) == len(tipos_payload)


@pytest.mark.parametrize(
    ("tipos_payload", "mensaje"),
    [
        ([], "EVIDENCIA_INICIO"),
        ([TIPO_GENERAL], "EVIDENCIA_INICIO"),
        ([TIPO_CIERRE], "EVIDENCIA_CIERRE"),
        (
            [TIPO_INICIO, TIPO_CIERRE],
            rf"(prohib|permit).*{TIPO_CIERRE}|{TIPO_CIERRE}.*(prohib|permit)",
        ),
    ],
)
def test_inicio_rechaza_matriz_no_permitida(
    db_session, escenario_evidencias, tipos_payload, mensaje
):
    viaje = escenario_evidencias["viaje"]
    payload = _payload([_evidencia_input(escenario_evidencias, tipo) for tipo in tipos_payload])

    with pytest.raises(ValueError, match=mensaje):
        iniciar_viaje(db_session, viaje, payload)


@pytest.mark.parametrize("campo_invalido", ["tipo", "archivo"])
def test_inicio_rechaza_referencias_inexistentes(db_session, escenario_evidencias, campo_invalido):
    evidencia = _evidencia_input(escenario_evidencias, TIPO_INICIO)
    if campo_invalido == "tipo":
        evidencia.id_tipo_evidencia = 999_999
    else:
        evidencia.id_archivo = 999_999

    with pytest.raises(ValueError, match="tipo de evidencia|archivo"):
        iniciar_viaje(db_session, escenario_evidencias["viaje"], _payload([evidencia]))


@pytest.mark.parametrize(
    "tipos_payload",
    [
        [TIPO_CIERRE],
        [TIPO_CIERRE, TIPO_CIERRE],
        [TIPO_CIERRE, TIPO_GENERAL],
        [TIPO_GENERAL, TIPO_CIERRE, TIPO_GENERAL],
    ],
)
def test_finalizacion_acepta_matriz_permitida(
    db_session, escenario_evidencias, tipos_payload
):
    _preparar_finalizacion(db_session, escenario_evidencias)
    viaje = escenario_evidencias["viaje"]
    payload = _payload(
        [_evidencia_input(escenario_evidencias, tipo) for tipo in tipos_payload],
        kilometraje=1200,
    )

    finalizar_viaje(db_session, viaje, payload)

    db_session.expire_all()
    persistido = db_session.get(Viaje, viaje.id_viaje)
    evidencias = db_session.query(Evidencia).filter_by(id_viaje=viaje.id_viaje).all()
    assert persistido.estatus_actual.clave == "FINALIZADO"
    assert len(evidencias) == len(tipos_payload)


@pytest.mark.parametrize(
    ("tipos_payload", "mensaje"),
    [
        ([], "EVIDENCIA_CIERRE"),
        ([TIPO_GENERAL], "EVIDENCIA_CIERRE"),
        ([TIPO_INICIO], "EVIDENCIA_INICIO"),
        (
            [TIPO_CIERRE, TIPO_INICIO],
            rf"(prohib|permit).*{TIPO_INICIO}|{TIPO_INICIO}.*(prohib|permit)",
        ),
    ],
)
def test_finalizacion_rechaza_matriz_no_permitida(
    db_session, escenario_evidencias, tipos_payload, mensaje
):
    _preparar_finalizacion(db_session, escenario_evidencias)
    payload = _payload(
        [_evidencia_input(escenario_evidencias, tipo) for tipo in tipos_payload],
        kilometraje=1200,
    )

    with pytest.raises(ValueError, match=mensaje):
        finalizar_viaje(db_session, escenario_evidencias["viaje"], payload)


@pytest.mark.parametrize("campo_invalido", ["tipo", "archivo"])
def test_finalizacion_rechaza_referencias_inexistentes(
    db_session, escenario_evidencias, campo_invalido
):
    _preparar_finalizacion(db_session, escenario_evidencias)
    evidencia = _evidencia_input(escenario_evidencias, TIPO_CIERRE)
    if campo_invalido == "tipo":
        evidencia.id_tipo_evidencia = 999_999
    else:
        evidencia.id_archivo = 999_999

    with pytest.raises(ValueError, match="tipo de evidencia|archivo"):
        finalizar_viaje(
            db_session,
            escenario_evidencias["viaje"],
            _payload([evidencia], kilometraje=1200),
        )


def test_inicio_exitoso_persiste_evento_evidencias_historial_y_estado(
    db_session, escenario_evidencias
):
    viaje = escenario_evidencias["viaje"]
    iniciar_viaje(
        db_session,
        viaje,
        _payload(
            [
                _evidencia_input(escenario_evidencias, TIPO_INICIO),
                _evidencia_input(escenario_evidencias, TIPO_GENERAL),
            ]
        ),
    )

    db_session.expire_all()
    evento = db_session.query(EventoOperativoViaje).filter_by(id_viaje=viaje.id_viaje).one()
    evidencias = db_session.query(Evidencia).filter_by(id_viaje=viaje.id_viaje).all()
    historial = (
        db_session.query(HistorialEstatusViaje)
        .filter_by(id_viaje=viaje.id_viaje)
        .order_by(HistorialEstatusViaje.id_historial)
        .all()
    )
    assert evento.tipo_evento == "INICIO_VIAJE"
    assert {evidencia.id_evento_operativo for evidencia in evidencias} == {evento.id_evento}
    assert db_session.get(Viaje, viaje.id_viaje).estatus_actual.clave == "INICIADO"
    assert [item.estatus.clave for item in historial] == ["CARGANDO", "INICIADO"]


def test_finalizacion_exitosa_persiste_evento_evidencias_historial_y_estado(
    db_session, escenario_evidencias
):
    _preparar_finalizacion(db_session, escenario_evidencias)
    viaje = escenario_evidencias["viaje"]
    finalizar_viaje(
        db_session,
        viaje,
        _payload(
            [
                _evidencia_input(escenario_evidencias, TIPO_CIERRE),
                _evidencia_input(escenario_evidencias, TIPO_GENERAL),
            ],
            kilometraje=1200,
        ),
    )

    db_session.expire_all()
    evento = db_session.query(EventoOperativoViaje).filter_by(id_viaje=viaje.id_viaje).one()
    evidencias = db_session.query(Evidencia).filter_by(id_viaje=viaje.id_viaje).all()
    historial = (
        db_session.query(HistorialEstatusViaje)
        .filter_by(id_viaje=viaje.id_viaje)
        .order_by(HistorialEstatusViaje.id_historial)
        .all()
    )
    assert evento.tipo_evento == "FINALIZACION_VIAJE"
    assert {evidencia.id_evento_operativo for evidencia in evidencias} == {evento.id_evento}
    assert db_session.get(Viaje, viaje.id_viaje).estatus_actual.clave == "FINALIZADO"
    assert [item.estatus.clave for item in historial] == ["CARGANDO", "INICIADO", "FINALIZADO"]


@pytest.mark.parametrize(
    ("historica", "tipo_evento_historico", "accion", "estado_inicial", "kilometraje"),
    [
        (TIPO_INICIO, "INICIO_VIAJE", finalizar_viaje, "INICIADO", 1200),
        (TIPO_CIERRE, "FINALIZACION_VIAJE", iniciar_viaje, "CARGANDO", 1000),
    ],
)
def test_evidencia_historica_no_satisface_accion(
    db_session,
    escenario_evidencias,
    historica,
    tipo_evento_historico,
    accion,
    estado_inicial,
    kilometraje,
):
    if estado_inicial == "INICIADO":
        _preparar_finalizacion(db_session, escenario_evidencias)

    viaje = escenario_evidencias["viaje"]
    viaje.id_estatus_actual = escenario_evidencias["estados"][estado_inicial].id_estatus
    evento_historico = EventoOperativoViaje(
        id_viaje=viaje.id_viaje,
        id_operador=escenario_evidencias["operador"].id_operador,
        id_trailer=escenario_evidencias["trailer"].id_trailer,
        id_caja=escenario_evidencias["caja"].id_caja,
        tipo_evento=tipo_evento_historico,
        kilometraje=900,
        nivel_diesel=80,
        ubicacion="Ubicación histórica",
        latitud=25.40,
        longitud=-100.90,
    )
    db_session.add(evento_historico)
    db_session.flush()
    evidencia = _evidencia_input(escenario_evidencias, historica)
    evidencia_historica = Evidencia(
        id_viaje=viaje.id_viaje,
        id_evento_operativo=evento_historico.id_evento,
        id_tipo_evidencia=evidencia.id_tipo_evidencia,
        id_archivo=evidencia.id_archivo,
        id_operador=escenario_evidencias["operador"].id_operador,
    )
    db_session.add(evidencia_historica)
    db_session.commit()
    evento_id = evento_historico.id_evento
    evidencia_id = evidencia_historica.id_evidencia
    snapshot_antes = _snapshot_atomico(db_session, viaje.id_viaje)

    with pytest.raises(ValueError, match="evidencia nueva|EVIDENCIA_"):
        accion(
            db_session,
            viaje,
            _payload([], kilometraje=kilometraje),
        )

    assert _snapshot_atomico(db_session, viaje.id_viaje) == snapshot_antes
    evento_persistido = db_session.get(EventoOperativoViaje, evento_id)
    evidencia_persistida = db_session.get(Evidencia, evidencia_id)
    assert evento_persistido is not None
    assert evento_persistido.tipo_evento == tipo_evento_historico
    assert evidencia_persistida is not None
    assert evidencia_persistida.id_evento_operativo == evento_id


def test_payload_parcialmente_invalido_no_deja_evento_ni_evidencias(
    db_session, escenario_evidencias
):
    viaje = escenario_evidencias["viaje"]
    invalida = _evidencia_input(escenario_evidencias, TIPO_GENERAL)
    invalida.id_archivo = 999_999
    snapshot_antes = _snapshot_atomico(db_session, viaje.id_viaje)

    with pytest.raises(ValueError, match="archivo"):
        iniciar_viaje(
            db_session,
            viaje,
            _payload([_evidencia_input(escenario_evidencias, TIPO_INICIO), invalida]),
        )

    assert _snapshot_atomico(db_session, viaje.id_viaje) == snapshot_antes


def test_fallo_documental_estricto_no_deja_evento_ni_evidencias(
    db_session, escenario_evidencias
):
    viaje = escenario_evidencias["viaje"]
    snapshot_antes = _snapshot_atomico(db_session, viaje.id_viaje)

    with _strict_evidence_validation(True):
        with pytest.raises(ValueError, match="documento"):
            iniciar_viaje(
                db_session,
                viaje,
                _payload([_evidencia_input(escenario_evidencias, TIPO_INICIO)]),
            )

    assert _snapshot_atomico(db_session, viaje.id_viaje) == snapshot_antes


def test_fallo_durante_accion_revierte_todas_las_mutaciones(
    db_session, escenario_evidencias
):
    viaje = escenario_evidencias["viaje"]
    snapshot_antes = _snapshot_atomico(db_session, viaje.id_viaje)

    def fallar_commit(session):
        raise RuntimeError("fallo transaccional inducido")

    event.listen(db_session, "before_commit", fallar_commit)
    try:
        with pytest.raises(RuntimeError, match="fallo transaccional inducido"):
            iniciar_viaje(
                db_session,
                viaje,
                _payload([_evidencia_input(escenario_evidencias, TIPO_INICIO)]),
            )
    finally:
        event.remove(db_session, "before_commit", fallar_commit)

    assert _snapshot_atomico(db_session, viaje.id_viaje) == snapshot_antes


@pytest.mark.parametrize("destino", ["INICIADO", "FINALIZADO"])
def test_endpoint_generico_bloquea_estados_operativos_sin_mutaciones(
    db_session, escenario_evidencias, destino
):
    viaje = escenario_evidencias["viaje"]
    if destino == "FINALIZADO":
        _preparar_finalizacion(db_session, escenario_evidencias)
    snapshot_antes = _snapshot_atomico(db_session, viaje.id_viaje)

    with pytest.raises(HTTPException) as exc_info:
        routes_viajes.cambiar_estatus(
            viaje.id_viaje,
            ViajeCambioEstatus(id_estatus_destino=escenario_evidencias["estados"][destino].id_estatus),
            db_session,
            escenario_evidencias["usuario"],
        )

    assert exc_info.value.status_code == 400
    endpoint_requerido = "/iniciar-viaje" if destino == "INICIADO" else "/finalizar"
    assert endpoint_requerido in str(exc_info.value.detail)
    assert _snapshot_atomico(db_session, viaje.id_viaje) == snapshot_antes


@pytest.mark.parametrize("destino", ["INICIADO", "FINALIZADO"])
def test_endpoint_generico_responde_http_400_con_endpoint_especifico(
    app, monkeypatch, destino
):
    destino_id = 4 if destino == "INICIADO" else 6
    estatus_destino = SimpleNamespace(id_estatus=destino_id, clave=destino)
    fake_db = FakeContractDbSession(estatus_destino)
    usuario = SimpleNamespace(
        id_usuario=2,
        username="operador_contract",
        activo=True,
        rol=SimpleNamespace(nombre="OPERADOR"),
        operador=SimpleNamespace(id_operador=10),
    )
    viaje = SimpleNamespace(
        id_viaje=1,
        id_estatus_actual=3 if destino == "INICIADO" else 4,
        estatus_actual=SimpleNamespace(
            clave="CARGANDO" if destino == "INICIADO" else "INICIADO",
            es_terminal=False,
        ),
        id_operador_actual=10,
        id_trailer_actual=20,
        id_caja_actual=30,
    )

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: usuario,
    )
    monkeypatch.setattr(routes_viajes, "_validar_acceso_viaje", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        routes_viajes,
        "_bloquear_operacion_operador_en_standby",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: viaje)

    def no_debe_delegar(*_args, **_kwargs):
        raise AssertionError("El endpoint genérico no debe delegar INICIADO ni FINALIZADO")

    monkeypatch.setattr(routes_viajes, "cambiar_estatus_viaje", no_debe_delegar)
    client = TestClient(app)
    try:
        response = client.post(
            "/viajes/1/cambiar-estatus",
            json={"id_estatus_destino": destino_id},
            headers=_auth_headers(usuario),
        )
    finally:
        app.dependency_overrides.clear()

    endpoint_requerido = "/iniciar-viaje" if destino == "INICIADO" else "/finalizar"
    assert response.status_code == 400
    assert endpoint_requerido in response.json()["detail"]


def test_endpoint_generico_conserva_error_para_destino_inexistente(
    db_session, escenario_evidencias
):
    with pytest.raises(HTTPException) as exc_info:
        routes_viajes.cambiar_estatus(
            escenario_evidencias["viaje"].id_viaje,
            ViajeCambioEstatus(id_estatus_destino=999_999),
            db_session,
            escenario_evidencias["usuario"],
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Estatus actual o destino inválido"


def test_endpoint_generico_conserva_transiciones_no_operativas(
    db_session, escenario_evidencias
):
    _preparar_finalizacion(db_session, escenario_evidencias)
    viaje = escenario_evidencias["viaje"]
    snapshot_antes = _snapshot_atomico(db_session, viaje.id_viaje)

    resultado = routes_viajes.cambiar_estatus(
        viaje.id_viaje,
        ViajeCambioEstatus(
            id_estatus_destino=escenario_evidencias["estados"]["RETRASADO"].id_estatus,
            comentario="Transición genérica permitida",
        ),
        db_session,
        escenario_evidencias["usuario"],
    )

    db_session.expire_all()
    snapshot_despues = _snapshot_atomico(db_session, viaje.id_viaje)
    assert resultado.id_estatus_actual == escenario_evidencias["estados"]["RETRASADO"].id_estatus
    assert db_session.get(Viaje, viaje.id_viaje).estatus_actual.clave == "RETRASADO"
    assert snapshot_despues["historial"] == snapshot_antes["historial"] + 1
    assert snapshot_despues["id_estatus_actual"] != snapshot_antes["id_estatus_actual"]
    for campo in (
        "eventos",
        "evidencias",
        "fecha_inicio",
        "fecha_llegada",
        "id_operador_actual",
        "id_trailer_actual",
        "id_caja_actual",
        "asignacion_activa",
        "fecha_inicio_operacion",
        "fecha_fin_asignacion",
    ):
        assert snapshot_despues[campo] == snapshot_antes[campo]
    assert db_session.query(EventoOperativoViaje).filter_by(id_viaje=viaje.id_viaje).count() == 0
    assert db_session.query(Evidencia).filter_by(id_viaje=viaje.id_viaje).count() == 0
