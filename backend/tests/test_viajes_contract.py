from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.deps import get_db


def _build_user(
    *,
    user_id: int = 1,
    username: str = "AdminGeneral",
    role: str = "ADMIN",
    activo: bool = True,
    operador_id: int | None = None,
):
    return SimpleNamespace(
        id_usuario=user_id,
        username=username,
        nombre="Usuario",
        apellido="Prueba",
        activo=activo,
        rol=SimpleNamespace(nombre=role),
        operador=SimpleNamespace(id_operador=operador_id) if operador_id is not None else None,
    )


class FakeDbSession:
    pass


def _override_db(app):
    def override_get_db():
        yield FakeDbSession()

    app.dependency_overrides[get_db] = override_get_db


def _auth_headers(*, user_id: int, username: str, role: str, operator_id: int | None = None):
    token = create_access_token(
        {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "operator_id": operator_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _viaje_record():
    return {
        "id_viaje": 1,
        "folio": "VJ-2026-0001",
        "folio_viaje_cliente": "CLI-001",
        "id_cliente": 1,
        "lugar_inicio": "Patio Saltillo",
        "lugar_destino": "Monterrey Centro",
        "lugar_inicio_latitud": None,
        "lugar_inicio_longitud": None,
        "lugar_destino_latitud": None,
        "lugar_destino_longitud": None,
        "tipo_carga": "General",
        "descripcion_carga": "Carga de prueba",
        "id_estatus_actual": 1,
        "id_operador_actual": 10,
        "id_trailer_actual": 20,
        "id_caja_actual": 30,
        "fecha_programada_salida": None,
        "fecha_carga": None,
        "hora_carga": None,
        "fecha_descarga": None,
        "hora_descarga": None,
        "fecha_inicio": None,
        "fecha_llegada": None,
        "fecha_entrega": None,
        "hora_entrega": None,
        "hora_cita_descarga": None,
        "observaciones": None,
        "created_by": 1,
        "updated_by": 1,
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
        "updated_at": datetime(2026, 1, 1, 12, 0, 0),
    }


def _viaje_model():
    return SimpleNamespace(
        id_viaje=1,
        id_estatus_actual=1,
        estatus_actual=SimpleNamespace(clave="ASIGNADO", es_terminal=False),
        id_operador_actual=10,
        id_trailer_actual=20,
        id_caja_actual=30,
    )


def _asignacion_record():
    return {
        "id_asignacion": 100,
        "id_viaje": 1,
        "id_operador": 10,
        "id_trailer": 20,
        "id_caja": 30,
        "activo": True,
        "fecha_asignacion": datetime(2026, 1, 1, 12, 0, 0),
        "fecha_inicio_operacion": None,
        "fecha_fin_asignacion": None,
        "motivo": "Asignacion inicial",
        "comentario": "Contrato de prueba",
        "created_by": 1,
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
    }


def test_create_viaje_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="ADMIN"),
    )
    monkeypatch.setattr(routes_viajes, "cliente_exists", lambda db, cliente_id: True)
    monkeypatch.setattr(routes_viajes, "create_viaje", lambda db, viaje_in, created_by=None: _viaje_record())
    client = TestClient(app)

    response = client.post(
        "/viajes/?created_by=1",
        json={
            "id_cliente": 1,
            "lugar_inicio": "Patio Saltillo",
            "lugar_destino": "Monterrey Centro",
            "folio_viaje_cliente": "CLI-001",
        },
        headers=_auth_headers(user_id=1, username="AdminGeneral", role="ADMIN"),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["folio"] == "VJ-2026-0001"


def test_asignar_viaje_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="ADMIN"),
    )
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(routes_viajes, "operador_exists", lambda db, operador_id: True)
    monkeypatch.setattr(routes_viajes, "trailer_exists", lambda db, trailer_id: True)
    monkeypatch.setattr(routes_viajes, "caja_exists", lambda db, caja_id: True)
    monkeypatch.setattr(routes_viajes, "create_asignacion_viaje", lambda db, db_viaje, asignacion_in: _asignacion_record())
    client = TestClient(app)

    response = client.post(
        "/viajes/1/asignar",
        json={
            "id_operador": 10,
            "id_trailer": 20,
            "id_caja": 30,
            "created_by": 1,
            "motivo": "Asignacion inicial",
            "comentario": "Contrato de prueba",
        },
        headers=_auth_headers(user_id=1, username="AdminGeneral", role="ADMIN"),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id_asignacion"] == 100


def test_iniciar_viaje_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="OPERADOR", operador_id=10),
    )
    monkeypatch.setattr(routes_viajes, "_validar_acceso_viaje", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "_bloquear_operacion_operador_en_standby", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(
        routes_viajes,
        "iniciar_viaje",
        lambda db, db_viaje, evento_in, changed_by=None, comentario=None: _viaje_record(),
    )
    client = TestClient(app)

    response = client.post(
        "/viajes/1/iniciar-viaje",
        json={
            "ubicacion": "Patio Saltillo",
            "latitud": 25.45,
            "longitud": -100.99,
            "comentario": "Salida operativa",
            "kilometraje": 1000,
            "nivel_diesel": 80,
            "evidencias": [],
        },
        headers=_auth_headers(user_id=2, username="OperadorUno", role="OPERADOR", operator_id=10),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id_viaje"] == 1


def test_cambiar_estatus_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="OPERADOR", operador_id=10),
    )
    monkeypatch.setattr(routes_viajes, "_validar_acceso_viaje", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "_bloquear_operacion_operador_en_standby", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(
        routes_viajes,
        "get_estatus_by_id",
        lambda db, estatus_id: SimpleNamespace(
            id_estatus=estatus_id,
            clave="CARGANDO",
        ),
    )
    monkeypatch.setattr(
        routes_viajes,
        "cambiar_estatus_viaje",
        lambda db, db_viaje, cambio_in: _viaje_record(),
    )
    client = TestClient(app)

    response = client.post(
        "/viajes/1/cambiar-estatus",
        json={
            "id_estatus_destino": 2,
            "changed_by": 2,
            "comentario": "Cambio de contrato",
        },
        headers=_auth_headers(user_id=2, username="OperadorUno", role="OPERADOR", operator_id=10),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id_viaje"] == 1


def test_solicitar_standby_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="OPERADOR", operador_id=10),
    )
    monkeypatch.setattr(routes_viajes, "_validar_acceso_viaje", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(routes_viajes, "solicitar_standby_viaje", lambda *args, **kwargs: SimpleNamespace(id_evento=1))
    client = TestClient(app)

    response = client.post(
        "/viajes/1/solicitar-standby",
        json={
            "ubicacion": "Patio Saltillo",
            "latitud": 25.45,
            "longitud": -100.99,
            "comentario": "Falla mecanica",
            "kilometraje": 1001,
            "nivel_diesel": 75,
            "evidencias": [],
        },
        headers=_auth_headers(user_id=2, username="OperadorUno", role="OPERADOR", operator_id=10),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["mensaje"] == "Solicitud registrada, pendiente de autorización administrativa"


def test_autorizar_standby_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="ADMIN"),
    )
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(routes_viajes, "get_solicitud_standby_pendiente", lambda db, db_viaje: SimpleNamespace(id_evento=1))
    monkeypatch.setattr(
        routes_viajes,
        "autorizar_standby_viaje",
        lambda db, db_viaje, changed_by=None: _viaje_record(),
    )
    client = TestClient(app)

    response = client.post(
        "/viajes/1/autorizar-standby",
        headers=_auth_headers(user_id=1, username="AdminGeneral", role="ADMIN"),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id_viaje"] == 1


def test_reiniciar_viaje_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="OPERADOR", operador_id=10),
    )
    monkeypatch.setattr(routes_viajes, "_validar_acceso_viaje", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(
        routes_viajes,
        "reiniciar_viaje",
        lambda db, db_viaje, evento_in, changed_by=None, comentario=None: _viaje_record(),
    )
    client = TestClient(app)

    response = client.post(
        "/viajes/1/reiniciar-viaje",
        json={
            "ubicacion": "Patio Saltillo",
            "latitud": 25.45,
            "longitud": -100.99,
            "comentario": "Reinicio operativo",
            "kilometraje": 300,
            "nivel_diesel": 60,
            "evidencias": [],
        },
        headers=_auth_headers(user_id=2, username="OperadorUno", role="OPERADOR", operator_id=10),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id_viaje"] == 1


def test_finalizar_viaje_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="OPERADOR", operador_id=10),
    )
    monkeypatch.setattr(routes_viajes, "_validar_acceso_viaje", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "_bloquear_operacion_operador_en_standby", lambda *args, **kwargs: None)
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(
        routes_viajes,
        "finalizar_viaje",
        lambda db, db_viaje, evento_in, changed_by=None, comentario=None: _viaje_record(),
    )
    client = TestClient(app)

    response = client.post(
        "/viajes/1/finalizar",
        json={
            "ubicacion": "Monterrey Centro",
            "latitud": 25.68,
            "longitud": -100.31,
            "comentario": "Entrega completada",
            "kilometraje": 1200,
            "nivel_diesel": 40,
            "evidencias": [],
        },
        headers=_auth_headers(user_id=2, username="OperadorUno", role="OPERADOR", operator_id=10),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id_viaje"] == 1


def test_cancelar_viaje_contract(app, monkeypatch):
    from app.api import deps_auth, routes_viajes

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="ADMIN"),
    )
    monkeypatch.setattr(routes_viajes, "get_viaje_by_id", lambda db, viaje_id: _viaje_model())
    monkeypatch.setattr(
        routes_viajes,
        "cancelar_viaje",
        lambda db, db_viaje, changed_by=None, comentario=None: _viaje_record(),
    )
    client = TestClient(app)

    response = client.post(
        "/viajes/1/cancelar",
        json={
            "changed_by": 1,
            "comentario": "Cancelado por pruebas",
        },
        headers=_auth_headers(user_id=1, username="AdminGeneral", role="ADMIN"),
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id_viaje"] == 1
