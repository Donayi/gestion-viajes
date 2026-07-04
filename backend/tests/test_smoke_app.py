from fastapi.testclient import TestClient


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


def test_db_ping_endpoint_exists_with_overridden_db(app):
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

    def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/db/ping")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"database": "connected", "result": 1}


def test_openapi_json_endpoint(app):
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert "openapi" in payload
    assert "paths" in payload
