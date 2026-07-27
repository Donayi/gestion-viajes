from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.deps import get_db


ADMIN = {"user_id": 1, "username": "AdminGeneral", "role": "ADMIN", "operador_id": None}
OPERADOR = {"user_id": 2, "username": "OperadorUno", "role": "OPERADOR", "operador_id": 10}
MANTENIMIENTO = {"user_id": 3, "username": "TecnicoUno", "role": "MANTENIMIENTO", "operador_id": None}


class FakeDbSession:
    pass


def _override_db(app):
    def override_get_db():
        yield FakeDbSession()

    app.dependency_overrides[get_db] = override_get_db


def _build_user(*, user_id: int, username: str, role: str, operador_id: int | None):
    return SimpleNamespace(
        id_usuario=user_id,
        username=username,
        nombre="Usuario",
        apellido="Prueba",
        activo=True,
        rol=SimpleNamespace(nombre=role),
        operador=SimpleNamespace(id_operador=operador_id) if operador_id is not None else None,
    )


def _set_current_user(monkeypatch, profile: dict[str, object]):
    from app.api import deps_auth

    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(**profile),
    )


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


def _empty_dashboard_payload():
    return {
        "generated_at": datetime(2026, 7, 27, 12, 0, tzinfo=UTC),
        "viajes_resumen": {
            "total": 0,
            "activos": 0,
            "finalizados": 0,
            "standby": 0,
            "cancelados": 0,
            "sin_ubicacion": 0,
            "por_estatus": [],
        },
        "kpis_operativos": {
            "total_viajes_con_eventos": 0,
            "km_total_recorridos": 0.0,
            "km_promedio_por_viaje": 0.0,
            "diesel_total_consumido_estimado": 0.0,
            "diesel_promedio_consumido": 0.0,
            "numero_total_standbys": 0,
            "viajes_finalizados_con_kpi": 0,
        },
        "disponibilidad": {
            "operadores": {"total": 0, "disponibles": 0, "ocupados": 0, "inactivos": 0},
            "trailers": {
                "total": 0,
                "disponibles": 0,
                "ocupados": 0,
                "en_mantenimiento": 0,
                "inactivos": 0,
            },
            "cajas": {
                "total": 0,
                "disponibles": 0,
                "ocupadas": 0,
                "en_mantenimiento": 0,
                "inactivas": 0,
            },
        },
        "alertas": {"pendientes_total": 0, "criticas_no_leidas": 0, "items": []},
        "mantenimientos": {
            "abiertos_total": 0,
            "en_proceso_total": 0,
            "proximos_total": 0,
            "items": [],
        },
        "mapa": {"total_con_ubicacion": 0, "total_sin_ubicacion": 0, "items": []},
    }


@pytest.fixture()
def client(monkeypatch):
    from app.main import app

    _override_db(app)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_dashboard_admin_requires_authentication(client):
    response = client.get("/dashboard/admin")
    assert response.status_code == 401


def test_dashboard_admin_rejects_operador(client, monkeypatch):
    _set_current_user(monkeypatch, OPERADOR)
    response = client.get("/dashboard/admin", headers=_auth_headers(OPERADOR))
    assert response.status_code == 403


def test_dashboard_admin_rejects_mantenimiento(client, monkeypatch):
    _set_current_user(monkeypatch, MANTENIMIENTO)
    response = client.get("/dashboard/admin", headers=_auth_headers(MANTENIMIENTO))
    assert response.status_code == 403


def test_dashboard_admin_returns_empty_contract_for_admin(client, monkeypatch):
    from app.api import routes_dashboard

    _set_current_user(monkeypatch, ADMIN)
    monkeypatch.setattr(routes_dashboard, "get_admin_dashboard", lambda db: deepcopy(_empty_dashboard_payload()))

    response = client.get("/dashboard/admin", headers=_auth_headers(ADMIN))

    assert response.status_code == 200
    payload = response.json()
    assert payload["viajes_resumen"]["por_estatus"] == []
    assert payload["alertas"]["items"] == []
    assert payload["mantenimientos"]["items"] == []
    assert payload["mapa"]["items"] == []
    assert payload["disponibilidad"]["trailers"]["en_mantenimiento"] == 0


def test_dashboard_admin_returns_stable_contract_without_heavy_fields(client, monkeypatch):
    from app.api import routes_dashboard

    _set_current_user(monkeypatch, ADMIN)
    payload = deepcopy(_empty_dashboard_payload())
    payload["viajes_resumen"] = {
        "total": 7,
        "activos": 4,
        "finalizados": 2,
        "standby": 1,
        "cancelados": 1,
        "sin_ubicacion": 3,
        "por_estatus": [
            {"clave": "ASIGNADO", "nombre": "Asignado", "total": 2},
            {"clave": "FINALIZADO", "nombre": "Finalizado", "total": 2},
        ],
    }
    payload["alertas"] = {
        "pendientes_total": 9,
        "criticas_no_leidas": 4,
        "items": [
            {
                "id_alerta": index,
                "tipo_alerta": "STANDBY_SOLICITADO",
                "entidad_tipo": "VIAJE",
                "entidad_id": index,
                "mensaje": f"Alerta {index}",
                "nivel": "CRITICAL",
                "leida": False,
                "created_at": datetime(2026, 7, 27, 12, index, tzinfo=UTC),
            }
            for index in range(1, 6)
        ],
    }
    payload["mantenimientos"] = {
        "abiertos_total": 6,
        "en_proceso_total": 3,
        "proximos_total": 2,
        "items": [
            {
                "id_mantenimiento": index,
                "entidad_tipo": "TRAILER",
                "entidad_id": index,
                "tipo_mantenimiento": "PREVENTIVO",
                "estatus": "ABIERTO",
                "fecha_inicio": datetime(2026, 7, 27, 8, 0, tzinfo=UTC),
                "fecha_mantenimiento": None,
                "fecha_proximo_mantenimiento": "2026-07-29",
                "descripcion": f"Mantenimiento {index}",
                "entidad": {"id": index, "etiqueta": f"TR-{index:03d}", "subtitulo": f"PLA-{index:03d}"},
            }
            for index in range(1, 6)
        ],
    }
    payload["mapa"] = {
        "total_con_ubicacion": 60,
        "total_sin_ubicacion": 5,
        "items": [
            {
                "id_viaje": index,
                "folio": f"VJ-2026-{index:04d}",
                "folio_viaje_cliente": None,
                "cliente": {"id_cliente": 1, "nombre_razon_social": "Cliente Demo", "rfc": None},
                "estatus_actual": {
                    "id_estatus": 2,
                    "clave": "ASIGNADO",
                    "nombre": "Asignado",
                    "es_terminal": False,
                    "requiere_evidencia": False,
                },
                "operador_actual": None,
                "trailer_actual": None,
                "caja_actual": None,
                "lugar_inicio": "Origen",
                "lugar_destino": "Destino",
                "lugar_inicio_latitud": None,
                "lugar_inicio_longitud": None,
                "lugar_destino_latitud": None,
                "lugar_destino_longitud": None,
                "ultima_ubicacion": {
                    "latitud": 25.0,
                    "longitud": -100.0,
                    "ubicacion": "Ruta",
                    "tipo_evento": "INICIO_VIAJE",
                    "created_at": datetime(2026, 7, 27, 11, 0, tzinfo=UTC),
                },
                "fecha_carga": None,
                "hora_carga": None,
                "fecha_descarga": None,
                "hora_descarga": None,
            }
            for index in range(1, 51)
        ],
    }
    monkeypatch.setattr(routes_dashboard, "get_admin_dashboard", lambda db: payload)

    response = client.get("/dashboard/admin", headers=_auth_headers(ADMIN))

    assert response.status_code == 200
    body = response.json()
    assert body["alertas"]["pendientes_total"] == 9
    assert body["mantenimientos"]["abiertos_total"] == 6
    assert body["mapa"]["total_con_ubicacion"] == 60
    assert len(body["alertas"]["items"]) == 5
    assert len(body["mantenimientos"]["items"]) == 5
    assert len(body["mapa"]["items"]) == 50
    assert body["alertas"]["items"][0]["nivel"] == "CRITICAL"
    assert body["mantenimientos"]["items"][0]["entidad_id"] == 1

    forbidden_keys = {"evidencias", "archivos", "checklist", "eventos_operativos", "historial"}
    assert forbidden_keys.isdisjoint(body.keys())
    for item in body["mantenimientos"]["items"]:
        assert forbidden_keys.isdisjoint(item.keys())
    for item in body["mapa"]["items"]:
        assert forbidden_keys.isdisjoint(item.keys())


def test_get_admin_dashboard_sets_timezone_aware_generated_at(monkeypatch):
    from app.api import routes_dashboard
    from app.schemas.kpi_operativo import KpiOperativoResumenResponse
    from app.main import app

    _override_db(app)
    _set_current_user(monkeypatch, ADMIN)
    monkeypatch.setattr(
        routes_dashboard,
        "get_admin_dashboard",
        lambda db: __import__("app.crud.crud_dashboard", fromlist=["get_admin_dashboard"])
        .get_admin_dashboard(db),
    )
    monkeypatch.setattr(
        __import__("app.crud.crud_dashboard", fromlist=["_get_viajes_resumen"]),
        "_get_viajes_resumen",
        lambda db, total_sin_ubicacion: {
            "total": 0,
            "activos": 0,
            "finalizados": 0,
            "standby": 0,
            "cancelados": 0,
            "sin_ubicacion": total_sin_ubicacion,
            "por_estatus": [],
        },
    )
    monkeypatch.setattr(
        __import__("app.crud.crud_dashboard", fromlist=["_get_kpis_operativos_resumen"]),
        "_get_kpis_operativos_resumen",
        lambda db: KpiOperativoResumenResponse(
            total_viajes_con_eventos=0,
            km_total_recorridos=0.0,
            km_promedio_por_viaje=0.0,
            diesel_total_consumido_estimado=0.0,
            diesel_promedio_consumido=0.0,
            numero_total_standbys=0,
            viajes_finalizados_con_kpi=0,
        ),
    )
    monkeypatch.setattr(
        __import__("app.crud.crud_dashboard", fromlist=["_get_disponibilidad_payload"]),
        "_get_disponibilidad_payload",
        lambda db: deepcopy(_empty_dashboard_payload()["disponibilidad"]),
    )
    monkeypatch.setattr(
        __import__("app.crud.crud_dashboard", fromlist=["_get_alertas_payload"]),
        "_get_alertas_payload",
        lambda db: deepcopy(_empty_dashboard_payload()["alertas"]),
    )
    monkeypatch.setattr(
        __import__("app.crud.crud_dashboard", fromlist=["_get_mantenimientos_payload"]),
        "_get_mantenimientos_payload",
        lambda db: deepcopy(_empty_dashboard_payload()["mantenimientos"]),
    )
    monkeypatch.setattr(
        __import__("app.crud.crud_dashboard", fromlist=["get_viajes_mapa"]),
        "get_viajes_mapa",
        lambda db, estatus_claves=None, incluir_finalizados=True, incluir_cancelados=True: [],
    )

    with TestClient(app) as client:
        response = client.get("/dashboard/admin", headers=_auth_headers(ADMIN))

    app.dependency_overrides.clear()

    assert response.status_code == 200
    generated_at = datetime.fromisoformat(response.json()["generated_at"].replace("Z", "+00:00"))
    assert generated_at.tzinfo is not None
    assert generated_at.utcoffset() == UTC.utcoffset(generated_at)


def test_dashboard_builders_apply_limits_and_keep_totals():
    from app.crud.crud_dashboard import (
        _build_alertas_payload,
        _build_mantenimientos_payload,
        _build_mapa_payload,
    )

    alert_items = [
        SimpleNamespace(
            id_alerta=index,
            tipo_alerta="VIAJE_CREADO",
            entidad_tipo="VIAJE",
            entidad_id=index,
            mensaje=f"Alerta {index}",
            nivel="INFO",
            leida=False,
            created_at=datetime(2026, 7, 27, 12, index, tzinfo=UTC),
        )
        for index in range(1, 9)
    ]
    mantenimiento_items = [
        SimpleNamespace(
            id_mantenimiento=index,
            entidad_tipo="TRAILER",
            entidad_id=index,
            tipo_mantenimiento="PREVENTIVO",
            estatus="ABIERTO",
            fecha_inicio=datetime(2026, 7, 27, 8, 0, tzinfo=UTC),
            fecha_mantenimiento=None,
            fecha_proximo_mantenimiento=None,
            descripcion=f"Item {index}",
            entidad={"id": index, "etiqueta": f"TR-{index:03d}", "subtitulo": None},
        )
        for index in range(1, 9)
    ]
    mapa_items = [
        {
            "id_viaje": index,
            "folio": f"VJ-{index}",
            "folio_viaje_cliente": None,
            "cliente": {"id_cliente": 1, "nombre_razon_social": "Cliente", "rfc": None},
            "estatus_actual": {
                "id_estatus": 1,
                "clave": "ASIGNADO",
                "nombre": "Asignado",
                "es_terminal": False,
                "requiere_evidencia": False,
            },
            "operador_actual": None,
            "trailer_actual": None,
            "caja_actual": None,
            "lugar_inicio": "Origen",
            "lugar_destino": "Destino",
            "lugar_inicio_latitud": None,
            "lugar_inicio_longitud": None,
            "lugar_destino_latitud": None,
            "lugar_destino_longitud": None,
            "ultima_ubicacion": (
                {
                    "latitud": 25.0,
                    "longitud": -100.0,
                    "ubicacion": "Ruta",
                    "tipo_evento": "INICIO_VIAJE",
                    "created_at": datetime(2026, 7, 27, 10, 0, tzinfo=UTC),
                }
                if index <= 52
                else None
            ),
            "fecha_carga": None,
            "hora_carga": None,
            "fecha_descarga": None,
            "hora_descarga": None,
        }
        for index in range(1, 56)
    ]

    alertas = _build_alertas_payload(
        pendientes_total=14,
        criticas_no_leidas=4,
        items=alert_items,
    )
    mantenimientos = _build_mantenimientos_payload(
        abiertos_total=11,
        en_proceso_total=3,
        proximos_total=6,
        items=mantenimiento_items,
    )
    mapa = _build_mapa_payload(mapa_items)

    assert len(alertas.items) == 5
    assert alertas.pendientes_total == 14
    assert alertas.criticas_no_leidas == 4
    assert alertas.items[0].nivel == "INFO"
    assert len(mantenimientos.items) == 5
    assert mantenimientos.abiertos_total == 11
    assert mantenimientos.en_proceso_total == 3
    assert mantenimientos.proximos_total == 6
    assert mantenimientos.items[0].entidad_id == 1
    assert len(mapa.items) == 50
    assert mapa.total_con_ubicacion == 52
    assert mapa.total_sin_ubicacion == 3
