from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.deps import get_db


ADMIN = {"user_id": 1, "username": "AdminGeneral", "role": "ADMIN", "operador_id": None}
OPERADOR = {"user_id": 2, "username": "OperadorUno", "role": "OPERADOR", "operador_id": 10}
OPERADOR_SIN_PERFIL = {"user_id": 2, "username": "OperadorSinPerfil", "role": "OPERADOR", "operador_id": None}
MANTENIMIENTO = {"user_id": 99, "username": "TecnicoUno", "role": "MANTENIMIENTO", "operador_id": None}

AUTH_REQUIRED_CASES = [
    "/viajes/mapa",
    "/viajes/kpis-operativos",
    "/kpis/operadores",
    "/kpis/trailers",
    "/kpis/clientes",
    "/alertas",
    "/mantenimientos",
]

ADMIN_ONLY_CASES = [
    "/viajes/mapa",
    "/kpis/operadores",
    "/kpis/trailers",
    "/kpis/clientes",
    "/alertas",
]

KPI_ENDPOINT_CASES = [
    {
        "route": "/kpis/operadores",
        "crud_name": "get_kpis_operadores",
        "response_factory": "kpi_operadores",
        "top_level_keys": {"periodo", "operadores", "series_semanales", "series_mensuales"},
        "first_list_key": "operadores",
        "field_name": "nombre_operador",
        "field_value": "Operador Demo",
    },
    {
        "route": "/kpis/trailers",
        "crud_name": "get_kpis_trailers",
        "response_factory": "kpi_trailers",
        "top_level_keys": {"periodo", "trailers"},
        "first_list_key": "trailers",
        "field_name": "numero_economico",
        "field_value": "TR-001",
    },
    {
        "route": "/kpis/clientes",
        "crud_name": "get_kpis_clientes",
        "response_factory": "kpi_clientes",
        "top_level_keys": {"periodo", "clientes"},
        "first_list_key": "clientes",
        "field_name": "nombre_razon_social",
        "field_value": "Cliente Demo SA de CV",
    },
]


def _build_user(*, user_id: int, username: str, role: str, operador_id: int | None, activo: bool = True):
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


def _auth_headers(profile: dict[str, object]) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": str(profile["user_id"]),
            "username": profile["username"],
            "role": profile["role"],
            "operator_id": profile["operador_id"],
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _set_current_user(monkeypatch, profile: dict[str, object]):
    from app.api import deps_auth

    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(**profile),
    )


def _payloads() -> dict[str, dict]:
    return {
        "mapa": {
            "id_viaje": 1,
            "folio": "VJ-2026-0001",
            "folio_viaje_cliente": "CLI-001",
            "cliente": {"id_cliente": 1, "nombre_razon_social": "Cliente Demo", "rfc": "XAXX010101000"},
            "estatus_actual": {
                "id_estatus": 2,
                "clave": "ASIGNADO",
                "nombre": "Asignado",
                "es_terminal": False,
                "requiere_evidencia": False,
            },
            "operador_actual": {"id_operador": 10, "alias": "Operador Demo"},
            "trailer_actual": {"id_trailer": 20, "numero_economico": "TR-001", "placas": "ABC123D"},
            "caja_actual": {"id_caja": 30, "numero_economico": "CJ-001", "placas": "XYZ987K"},
            "lugar_inicio": "Patio Saltillo",
            "lugar_destino": "Monterrey Centro",
            "lugar_inicio_latitud": 25.45,
            "lugar_inicio_longitud": -100.98,
            "lugar_destino_latitud": 25.67,
            "lugar_destino_longitud": -100.31,
            "ultima_ubicacion": {
                "latitud": 25.5,
                "longitud": -100.9,
                "ubicacion": "Carretera 57",
                "tipo_evento": "INICIO_VIAJE",
                "created_at": datetime(2026, 1, 1, 12, 0, 0),
            },
            "fecha_carga": date(2026, 1, 1),
            "hora_carga": "08:00:00",
            "fecha_descarga": date(2026, 1, 2),
            "hora_descarga": "18:00:00",
        },
        "kpi_operativo": {
            "resumen": {
                "total_viajes_con_eventos": 1,
                "km_total_recorridos": 200.0,
                "km_promedio_por_viaje": 200.0,
                "diesel_total_consumido_estimado": 30.0,
                "diesel_promedio_consumido": 30.0,
                "numero_total_standbys": 0,
                "viajes_finalizados_con_kpi": 1,
            },
            "viajes": [
                {
                    "id_viaje": 1,
                    "folio": "VJ-2026-0001",
                    "cliente": "Cliente Demo",
                    "operador": "Operador Demo",
                    "km_inicio": 1000.0,
                    "km_final": 1200.0,
                    "km_recorridos": 200.0,
                    "diesel_inicio": 80.0,
                    "diesel_final": 50.0,
                    "diesel_consumido": 30.0,
                    "numero_standbys": 0,
                    "ubicacion_inicio": "Patio Saltillo",
                    "ubicacion_final": "Monterrey Centro",
                    "fecha_inicio": datetime(2026, 1, 1, 8, 0, 0),
                    "fecha_finalizacion": datetime(2026, 1, 1, 18, 0, 0),
                    "kpi_completo": True,
                    "kpi_valido": True,
                    "anomalia": None,
                }
            ],
        },
        "kpi_operadores": {
            "periodo": {"fecha_desde": None, "fecha_hasta": None},
            "total_viajes_semana": 3,
            "total_viajes_mes": 8,
            "total_km_recorridos": 820.0,
            "series_semanales": [{"etiqueta": "Semana actual", "valor": 3}],
            "series_mensuales": [{"etiqueta": "Mes actual", "valor": 8}],
            "operadores": [
                {
                    "id_operador": 10,
                    "nombre": "Operador Demo",
                    "nombre_operador": "Operador Demo",
                    "nombre_completo": "Juan Perez",
                    "viajes_semana": 3,
                    "viajes_mes": 8,
                    "km_recorridos": 820.0,
                }
            ],
        },
        "kpi_trailers": {
            "periodo": {"fecha_desde": None, "fecha_hasta": None},
            "total_km_recorridos": 1200.0,
            "total_diesel_consumido_pct": 80.0,
            "rendimiento_promedio_km_por_pct_diesel": 15.0,
            "trailers": [
                {
                    "id_trailer": 20,
                    "numero_economico": "TR-001",
                    "placas": "ABC123D",
                    "km_recorridos": 1200.0,
                    "diesel_consumido_pct": 80.0,
                    "rendimiento_km_por_pct_diesel": 15.0,
                    "viajes": [
                        {
                            "id_viaje": 1,
                            "folio": "VJ-2026-0001",
                            "id_trailer": 20,
                            "numero_economico": "TR-001",
                            "km_recorridos": 200.0,
                            "diesel_consumido_pct": 30.0,
                            "rendimiento_km_por_pct_diesel": 6.67,
                            "consumo_valido": True,
                        }
                    ],
                }
            ],
        },
        "kpi_clientes": {
            "periodo": {"fecha_desde": None, "fecha_hasta": None},
            "total_viajes_terminados_semana": 2,
            "total_viajes_terminados_mes": 8,
            "total_viajes_en_espera": 3,
            "series_semanales": [{"etiqueta": "Semana actual", "valor": 2}],
            "series_mensuales": [{"etiqueta": "Mes actual", "valor": 8}],
            "clientes": [
                {
                    "id_cliente": 1,
                    "nombre": "Cliente Demo",
                    "nombre_razon_social": "Cliente Demo SA de CV",
                    "viajes_terminados_semana": 2,
                    "viajes_terminados_mes": 8,
                    "viajes_en_espera": 3,
                }
            ],
        },
        "alerta": {
            "id_alerta": 1,
            "tipo_alerta": "VIAJE_CREADO",
            "entidad_tipo": "VIAJE",
            "entidad_id": 1,
            "mensaje": "Se creo un viaje de prueba",
            "nivel": "INFO",
            "leida": False,
            "requiere_notificacion": True,
            "notificada": False,
            "canal_notificacion": None,
            "fecha_notificacion": None,
            "created_at": datetime(2026, 1, 1, 12, 0, 0),
        },
        "mantenimiento": {
            "id_mantenimiento": 1,
            "entidad_tipo": "TRAILER",
            "entidad_id": 20,
            "id_trailer": 20,
            "id_caja": None,
            "tipo_mantenimiento": "PREVENTIVO",
            "estatus": "ABIERTO",
            "fecha_inicio": datetime(2026, 1, 1, 9, 0, 0),
            "fecha_mantenimiento": date(2026, 1, 1),
            "fecha_proximo_mantenimiento": date(2026, 2, 1),
            "fecha_fin": None,
            "kilometraje": 1000.0,
            "descripcion": "Servicio preventivo",
            "observaciones": None,
            "created_by": 99,
            "updated_by": None,
            "created_at": datetime(2026, 1, 1, 9, 0, 0),
            "updated_at": datetime(2026, 1, 1, 9, 0, 0),
            "entidad": {"id": 20, "etiqueta": "TR-001", "subtitulo": "ABC123D"},
            "checklist_items": [],
            "archivos": [],
        },
    }


@pytest.fixture
def client(app):
    _override_db(app)
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides(app):
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize("route", AUTH_REQUIRED_CASES)
def test_dashboard_sources_require_authentication(client, route):
    response = client.get(route)

    assert response.status_code == 401


@pytest.mark.parametrize("route", ADMIN_ONLY_CASES)
def test_admin_only_dashboard_sources_reject_non_admin(client, monkeypatch, route):
    _set_current_user(monkeypatch, OPERADOR)

    response = client.get(route, headers=_auth_headers(OPERADOR))

    assert response.status_code == 403
    assert response.json()["detail"] == "No tienes permisos para acceder a este recurso"


def test_viajes_mapa_allows_admin_and_returns_stable_shape(client, monkeypatch):
    from app.api import routes_viajes

    payload = _payloads()
    _set_current_user(monkeypatch, ADMIN)
    monkeypatch.setattr(routes_viajes, "get_viajes_mapa", lambda db, **kwargs: [deepcopy(payload["mapa"])])

    response = client.get("/viajes/mapa", headers=_auth_headers(ADMIN))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body
    assert {"id_viaje", "folio", "cliente", "estatus_actual", "ultima_ubicacion"}.issubset(body[0].keys())


def test_viajes_kpis_operativos_allows_operador_and_scopes_filter(client, monkeypatch):
    from app.api import routes_viajes

    captured = {}
    payload = _payloads()

    def fake_get_kpis_operativos_dashboard(db, filters):
        captured["id_operador"] = filters.id_operador
        captured["solo_completos"] = filters.solo_completos
        return deepcopy(payload["kpi_operativo"])

    _set_current_user(monkeypatch, OPERADOR)
    monkeypatch.setattr(routes_viajes, "get_kpis_operativos_dashboard", fake_get_kpis_operativos_dashboard)

    response = client.get(
        "/viajes/kpis-operativos?id_operador=999&solo_completos=true",
        headers=_auth_headers(OPERADOR),
    )

    assert response.status_code == 200
    body = response.json()
    assert {"resumen", "viajes"} == set(body.keys())
    assert {"total_viajes_con_eventos", "km_total_recorridos"}.issubset(body["resumen"].keys())
    assert captured["id_operador"] == 10
    assert captured["solo_completos"] is True


def test_viajes_kpis_operativos_rejects_operador_without_profile(client, monkeypatch):
    _set_current_user(monkeypatch, OPERADOR_SIN_PERFIL)

    response = client.get("/viajes/kpis-operativos", headers=_auth_headers(OPERADOR_SIN_PERFIL))

    assert response.status_code == 403
    assert response.json()["detail"] == "El usuario actual no tiene perfil de operador"


@pytest.mark.parametrize("case", KPI_ENDPOINT_CASES, ids=[case["route"] for case in KPI_ENDPOINT_CASES])
def test_kpi_catalog_endpoints_allow_admin_and_return_stable_shape(client, monkeypatch, case):
    from app.api import routes_kpis

    payload = _payloads()
    _set_current_user(monkeypatch, ADMIN)
    monkeypatch.setattr(
        routes_kpis,
        case["crud_name"],
        lambda db, **kwargs: deepcopy(payload[case["response_factory"]]),
    )

    response = client.get(case["route"], headers=_auth_headers(ADMIN))

    assert response.status_code == 200
    body = response.json()
    assert case["top_level_keys"].issubset(body.keys())
    assert body[case["first_list_key"]][0][case["field_name"]] == case["field_value"]


def test_alertas_allows_admin_and_supports_empty_state(client, monkeypatch):
    from app.api import routes_alertas

    _set_current_user(monkeypatch, ADMIN)
    monkeypatch.setattr(routes_alertas, "get_alertas", lambda db, **kwargs: [])

    response = client.get("/alertas", headers=_auth_headers(ADMIN))

    assert response.status_code == 200
    assert response.json() == []


def test_alertas_allows_admin_and_returns_stable_shape(client, monkeypatch):
    from app.api import routes_alertas

    payload = _payloads()
    _set_current_user(monkeypatch, ADMIN)
    monkeypatch.setattr(routes_alertas, "get_alertas", lambda db, **kwargs: [deepcopy(payload["alerta"])])

    response = client.get("/alertas", headers=_auth_headers(ADMIN))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body
    assert {
        "id_alerta",
        "tipo_alerta",
        "mensaje",
        "nivel",
        "leida",
        "requiere_notificacion",
        "notificada",
    }.issubset(body[0].keys())


def test_mantenimientos_rejects_operador_role(client, monkeypatch):
    _set_current_user(monkeypatch, OPERADOR)

    response = client.get("/mantenimientos", headers=_auth_headers(OPERADOR))

    assert response.status_code == 403
    assert response.json()["detail"] == "No tienes permisos para acceder a este recurso"


def test_mantenimientos_allows_admin_and_returns_stable_shape(client, monkeypatch):
    from app.api import routes_mantenimientos

    payload = _payloads()
    _set_current_user(monkeypatch, ADMIN)
    monkeypatch.setattr(
        routes_mantenimientos,
        "get_mantenimientos",
        lambda db, **kwargs: [deepcopy(payload["mantenimiento"])],
    )

    response = client.get("/mantenimientos", headers=_auth_headers(ADMIN))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body
    assert {
        "id_mantenimiento",
        "entidad_tipo",
        "tipo_mantenimiento",
        "estatus",
        "entidad",
        "checklist_items",
        "archivos",
    }.issubset(body[0].keys())


def test_mantenimientos_allows_mantenimiento_and_scopes_created_by(client, monkeypatch):
    from app.api import routes_mantenimientos

    captured = {}
    payload = _payloads()

    def fake_get_mantenimientos(db, entidad_tipo=None, estatus=None, created_by=None):
        captured["created_by"] = created_by
        captured["estatus"] = estatus
        return [deepcopy(payload["mantenimiento"])]

    _set_current_user(monkeypatch, MANTENIMIENTO)
    monkeypatch.setattr(routes_mantenimientos, "get_mantenimientos", fake_get_mantenimientos)

    response = client.get("/mantenimientos?estatus=ABIERTO", headers=_auth_headers(MANTENIMIENTO))

    assert response.status_code == 200
    assert captured["created_by"] == 99
    assert captured["estatus"] == "ABIERTO"
