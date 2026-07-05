from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.deps import get_db


def _build_user(*, user_id: int = 1, username: str = "AdminGeneral", role: str = "ADMIN", activo: bool = True):
    return SimpleNamespace(
        id_usuario=user_id,
        username=username,
        nombre="Usuario",
        apellido="Prueba",
        activo=activo,
        rol=SimpleNamespace(nombre=role),
        operador=None,
    )


class FakeDbSession:
    pass


def _override_db(app):
    def override_get_db():
        yield FakeDbSession()

    app.dependency_overrides[get_db] = override_get_db


def _cliente_record():
    return {
        "id_cliente": 1,
        "nombre_razon_social": "Cliente Demo",
        "rfc": "XAXX010101000",
        "direccion": None,
        "cp": None,
        "regimen_fiscal": None,
        "tiempo_credito": None,
        "contacto_nombre": None,
        "contacto_telefono": None,
        "contacto_email": None,
        "activo": True,
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
        "updated_at": datetime(2026, 1, 1, 12, 0, 0),
    }


def _operador_record():
    return {
        "id_operador": 1,
        "id_usuario": 10,
        "alias": "Operador Demo",
        "numero_licencia": None,
        "rfc": None,
        "curp": None,
        "numero_expediente_medico": None,
        "licencia_vigencia": None,
        "sua": None,
        "sua_vigencia": None,
        "estudio_medico": None,
        "activo": True,
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
        "updated_at": datetime(2026, 1, 1, 12, 0, 0),
    }


def _trailer_record():
    return {
        "id_trailer": 1,
        "numero_economico": "TR-001",
        "placas": "ABC123D",
        "marca": None,
        "modelo": None,
        "anio": None,
        "poliza_seguro": None,
        "seguro_vigencia": None,
        "tarjeta_circulacion": None,
        "tarjeta_vigencia": None,
        "permiso_circulacion": None,
        "numero_serie": None,
        "verificacion": None,
        "verificacion_vigencia": None,
        "activo": True,
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
        "updated_at": datetime(2026, 1, 1, 12, 0, 0),
    }


def _caja_record():
    return {
        "id_caja": 1,
        "numero_economico": "CJ-001",
        "placas": "XYZ987K",
        "tipo_caja": None,
        "marca": None,
        "modelo": None,
        "anio": None,
        "poliza_seguro": None,
        "seguro_vigencia": None,
        "tarjeta_circulacion": None,
        "tarjeta_vigencia": None,
        "numero_serie": None,
        "verificacion": None,
        "verificacion_vigencia": None,
        "activo": True,
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
        "updated_at": datetime(2026, 1, 1, 12, 0, 0),
    }


CATALOG_CASES = [
    {
        "route": "/clientes/",
        "route_module": "routes_clientes",
        "crud_name": "get_clientes",
        "record_factory": lambda: [_cliente_record()],
    },
    {
        "route": "/clientes/1",
        "route_module": "routes_clientes",
        "crud_name": "get_cliente_by_id",
        "record_factory": _cliente_record,
    },
    {
        "route": "/operadores/",
        "route_module": "routes_operadores",
        "crud_name": "get_operadores",
        "record_factory": lambda: [_operador_record()],
    },
    {
        "route": "/operadores/1",
        "route_module": "routes_operadores",
        "crud_name": "get_operador_by_id",
        "record_factory": _operador_record,
    },
    {
        "route": "/trailers/",
        "route_module": "routes_trailers",
        "crud_name": "get_trailers",
        "record_factory": lambda: [_trailer_record()],
    },
    {
        "route": "/trailers/1",
        "route_module": "routes_trailers",
        "crud_name": "get_trailer_by_id",
        "record_factory": _trailer_record,
    },
    {
        "route": "/cajas/",
        "route_module": "routes_cajas",
        "crud_name": "get_cajas",
        "record_factory": lambda: [_caja_record()],
    },
    {
        "route": "/cajas/1",
        "route_module": "routes_cajas",
        "crud_name": "get_caja_by_id",
        "record_factory": _caja_record,
    },
]


@pytest.mark.parametrize("case", CATALOG_CASES, ids=[case["route"] for case in CATALOG_CASES])
def test_master_catalog_routes_require_token(app, case):
    _override_db(app)
    client = TestClient(app)

    response = client.get(case["route"])

    app.dependency_overrides.clear()

    assert response.status_code == 401


@pytest.mark.parametrize("case", CATALOG_CASES, ids=[case["route"] for case in CATALOG_CASES])
def test_master_catalog_routes_reject_non_admin(app, monkeypatch, case):
    from app.api import deps_auth

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="OPERADOR"),
    )
    token = create_access_token(
        {
            "sub": "2",
            "username": "OperadorUno",
            "role": "OPERADOR",
            "operator_id": 10,
        }
    )
    client = TestClient(app)

    response = client.get(case["route"], headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "No tienes permisos para acceder a este recurso"


@pytest.mark.parametrize("case", CATALOG_CASES, ids=[case["route"] for case in CATALOG_CASES])
def test_master_catalog_routes_allow_admin(app, monkeypatch, case):
    from app.api import deps_auth, routes_cajas, routes_clientes, routes_operadores, routes_trailers

    route_module = {
        "routes_clientes": routes_clientes,
        "routes_operadores": routes_operadores,
        "routes_trailers": routes_trailers,
        "routes_cajas": routes_cajas,
    }[case["route_module"]]

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="ADMIN"),
    )
    monkeypatch.setattr(route_module, case["crud_name"], lambda *args, **kwargs: case["record_factory"]())
    token = create_access_token(
        {
            "sub": "1",
            "username": "AdminGeneral",
            "role": "ADMIN",
            "operator_id": None,
        }
    )
    client = TestClient(app)

    response = client.get(case["route"], headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
