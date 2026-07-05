from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.deps import get_db


def _build_user(*, user_id: int = 1, username: str = "AdminGeneral", activo: bool = True):
    return SimpleNamespace(
        id_usuario=user_id,
        username=username,
        nombre="Admin",
        apellido="General",
        activo=activo,
        rol=SimpleNamespace(nombre="ADMIN"),
        operador=None,
    )


class FakeDbSession:
    pass


def _override_db(app):
    def override_get_db():
        yield FakeDbSession()

    app.dependency_overrides[get_db] = override_get_db


def test_auth_login_valid_returns_bearer_token(app, monkeypatch):
    from app.api import routes_auth

    _override_db(app)
    monkeypatch.setattr(routes_auth, "authenticate_user", lambda db, username, password: _build_user())
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        data={"username": "AdminGeneral", "password": "secreto123"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]


def test_auth_login_invalid_returns_401(app, monkeypatch):
    from app.api import routes_auth

    _override_db(app)
    monkeypatch.setattr(routes_auth, "authenticate_user", lambda db, username, password: None)
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        data={"username": "AdminGeneral", "password": "incorrecta"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "Username o password incorrectos"


def test_auth_me_without_token_returns_401(app):
    client = TestClient(app)

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_me_with_valid_token_returns_current_user(app, monkeypatch):
    from app.api import deps_auth

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id),
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

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id_usuario": 1,
        "username": "AdminGeneral",
        "nombre": "Admin",
        "apellido": "General",
        "rol": "ADMIN",
        "id_operador": None,
    }


def test_auth_me_with_inactive_user_returns_403(app, monkeypatch):
    from app.api import deps_auth

    _override_db(app)
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _build_user(user_id=user_id, activo=False),
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

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "El usuario está inactivo"


def test_auth_me_with_invalid_token_returns_401(app):
    _override_db(app)
    client = TestClient(app)

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer token-corrupto"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "No fue posible validar las credenciales"
