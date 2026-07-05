from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.core.security import create_access_token


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


def test_import_app_main():
    import app.main as main_module

    assert hasattr(main_module, "app")
    assert callable(main_module.create_app)


def test_create_app_returns_fastapi_instance():
    from fastapi import FastAPI
    from app.main import create_app

    app = create_app()

    assert isinstance(app, FastAPI)


def test_health_endpoint(app):
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_ping_without_token_returns_401(app):
    client = TestClient(app)

    response = client.get("/db/ping")

    assert response.status_code == 401


def test_db_ping_with_admin_token_returns_response(app, monkeypatch):
    class FakeResult:
        @staticmethod
        def fetchone():
            class Row:
                ok = 1

            return Row()

    class FakeSession:
        @staticmethod
        def execute(_query):
            return FakeResult()

    from app.db.deps import get_db
    from app.api import deps_auth

    def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, role="ADMIN"),
    )
    token = create_access_token(
        {
            "sub": "1",
            "username": "AdminGeneral",
            "role": "ADMIN",
            "operator_id": None,
        }
    )
    client = TestClient(app)

    response = client.get("/db/ping", headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"database": "connected", "result": 1}


def test_db_ping_with_non_admin_token_returns_403(app, monkeypatch):
    class FakeSession:
        pass

    from app.db.deps import get_db
    from app.api import deps_auth

    def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db
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

    response = client.get("/db/ping", headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "No tienes permisos para acceder a este recurso"


def test_openapi_json_endpoint(app):
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert "openapi" in payload
    assert "paths" in payload
