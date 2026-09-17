from types import SimpleNamespace
from datetime import timedelta
import asyncio

import httpx
import pytest
from fastapi import Depends
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


def test_bootstrap_admin_blocked_by_default(app, monkeypatch):
    from app.api import routes_auth

    _override_db(app)
    monkeypatch.setattr(routes_auth, "admin_exists", lambda db: False)
    monkeypatch.setattr(routes_auth.settings, "bootstrap_admin_enabled", False)
    client = TestClient(app)

    response = client.post(
        "/auth/bootstrap-admin",
        json={
            "username": "AdminGeneral",
            "password": "secreto123",
            "nombre": "Admin",
            "apellido": "General",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "El bootstrap inicial de administrador está deshabilitado. "
        "Activa BOOTSTRAP_ADMIN_ENABLED=true para permitir esta operación."
    )


def test_bootstrap_admin_allowed_when_flag_enabled(app, monkeypatch):
    from app.api import routes_auth

    _override_db(app)
    monkeypatch.setattr(routes_auth, "admin_exists", lambda db: False)
    monkeypatch.setattr(routes_auth.settings, "bootstrap_admin_enabled", True)
    monkeypatch.setattr(
        routes_auth,
        "create_bootstrap_admin",
        lambda db, bootstrap_in: _build_user(),
    )
    client = TestClient(app)

    response = client.post(
        "/auth/bootstrap-admin",
        json={
            "username": "AdminGeneral",
            "password": "secreto123",
            "nombre": "Admin",
            "apellido": "General",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "id_usuario": 1,
        "username": "AdminGeneral",
        "nombre": "Admin",
        "apellido": "General",
        "rol": "ADMIN",
    }


def test_bootstrap_admin_keeps_existing_admin_behavior(app, monkeypatch):
    from app.api import routes_auth

    _override_db(app)
    monkeypatch.setattr(routes_auth, "admin_exists", lambda db: True)
    monkeypatch.setattr(routes_auth.settings, "bootstrap_admin_enabled", False)
    client = TestClient(app)

    response = client.post(
        "/auth/bootstrap-admin",
        json={
            "username": "AdminGeneral",
            "password": "secreto123",
            "nombre": "Admin",
            "apellido": "General",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ya existe un usuario administrador. El bootstrap inicial ya no esta disponible"
    )


def _observe_auth_context(app):
    from app.services.audit_context import get_audit_state

    contexts = []

    async def observed(scope, receive, send):
        try:
            await app(scope, receive, send)
        finally:
            state = get_audit_state(scope)
            if state is not None:
                contexts.append(state.context)

    return TestClient(observed), contexts


@pytest.mark.parametrize("role", ["ADMIN", "OPERADOR", "MANTENIMIENTO"])
def test_authenticated_audit_actor_uses_database_snapshots_once(app, monkeypatch, role):
    from app.api import deps_auth
    from app.api.deps_audit import get_audit_context
    from app.core.config import settings

    monkeypatch.setattr(settings, "audit_enabled", True)
    _override_db(app)
    loaded = _build_user(username="DatabaseUser")
    loaded.rol.nombre = role
    calls = {"decode": 0, "load": 0}
    real_decode = deps_auth.decode_access_token

    def decode(token):
        calls["decode"] += 1
        return real_decode(token)

    def load(db, user_id):
        calls["load"] += 1
        assert user_id == loaded.id_usuario
        return loaded

    monkeypatch.setattr(deps_auth, "decode_access_token", decode)
    monkeypatch.setattr(deps_auth, "get_user_with_role_and_operador", load)

    def before_auth(context=Depends(get_audit_context)):
        assert context.actor.tipo.value == "ANONIMO"
        return context

    @app.get("/_test/auth-context")
    def protected(context=Depends(before_auth), user=Depends(deps_auth.require_roles(role))):
        assert user is loaded
        return context.model_dump(mode="json")

    token = create_access_token({"sub": "1", "username": "ForgedClaim", "role": "ForgedRole"})
    client, contexts = _observe_auth_context(app)
    try:
        response = client.get("/_test/auth-context", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    actor = response.json()["actor"]
    assert actor == {
        "tipo": "USUARIO", "usuario_id": 1, "username_snapshot": "DatabaseUser",
        "nombre_snapshot": "Admin General", "rol_snapshot": role,
    }
    assert contexts[-1].actor.username_snapshot == "DatabaseUser"
    assert calls == {"decode": 1, "load": 1}
    assert token not in contexts[-1].model_dump_json()


@pytest.mark.parametrize("case,status", [("missing", 401), ("invalid", 401), ("expired", 401), ("unknown", 401), ("inactive", 403)])
def test_failed_auth_stays_anonymous_and_preserves_http_behavior(app, monkeypatch, case, status):
    from app.api import deps_auth
    from app.core.config import settings

    monkeypatch.setattr(settings, "audit_enabled", True)
    _override_db(app)
    monkeypatch.setattr(
        deps_auth, "get_user_with_role_and_operador",
        lambda db, user_id: None if case == "unknown" else _build_user(activo=case != "inactive"),
    )
    token = "invalid-token" if case == "invalid" else create_access_token(
        {"sub": "1"}, expires_delta=timedelta(seconds=-10) if case == "expired" else None
    )
    headers = {} if case == "missing" else {"Authorization": f"Bearer {token}"}
    client, contexts = _observe_auth_context(app)
    try:
        response = client.get("/auth/me", headers=headers)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == status
    actor = contexts[-1].actor
    assert actor.tipo.value == "ANONIMO"
    assert actor.usuario_id is None
    assert actor.username_snapshot is None


def test_permission_denied_keeps_validated_actor(app, monkeypatch):
    from app.api import deps_auth
    from app.core.config import settings

    monkeypatch.setattr(settings, "audit_enabled", True)
    _override_db(app)
    loaded = _build_user()
    loaded.rol.nombre = "OPERADOR"
    monkeypatch.setattr(deps_auth, "get_user_with_role_and_operador", lambda db, user_id: loaded)
    client, contexts = _observe_auth_context(app)
    token = create_access_token({"sub": "1", "role": "ADMIN"})
    try:
        response = client.get("/db/ping", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert contexts[-1].actor.tipo.value == "USUARIO"
    assert contexts[-1].actor.rol_snapshot == "OPERADOR"


def test_disabled_audit_does_not_change_me_or_copy_user_snapshots(app, monkeypatch):
    from app.api import deps_auth
    from app.core.config import settings

    monkeypatch.setattr(settings, "audit_enabled", False)
    _override_db(app)
    monkeypatch.setattr(deps_auth, "get_user_with_role_and_operador", lambda db, user_id: _build_user())
    client, contexts = _observe_auth_context(app)
    token = create_access_token({"sub": "1"})
    try:
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["username"] == "AdminGeneral"
    assert contexts[-1].actor.tipo.value == "ANONIMO"
    assert contexts[-1].actor.username_snapshot is None
    assert contexts[-1].user_agent is None
    assert contexts[-1].ip_hash is None


def test_login_body_and_issued_token_never_enter_audit_context(app, monkeypatch):
    from app.api import routes_auth
    from app.core.config import settings

    monkeypatch.setattr(settings, "audit_enabled", True)
    _override_db(app)
    monkeypatch.setattr(routes_auth, "authenticate_user", lambda db, username, password: _build_user())
    client, contexts = _observe_auth_context(app)
    try:
        response = client.post("/auth/login", data={
            "username": "AdminGeneral", "password": "body-password-must-not-be-copied",
        }, headers={"Cookie": "session=secret-cookie", "X-Secret": "secret-header"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    token = response.json()["access_token"]
    rendered = contexts[-1].model_dump_json() + repr(contexts[-1])
    for secret in (token, "body-password-must-not-be-copied", "secret-cookie", "secret-header"):
        assert secret not in rendered
    assert contexts[-1].actor.tipo.value == "ANONIMO"


def test_concurrent_authenticated_requests_do_not_mix_actors(app, monkeypatch):
    from app.api import deps_auth
    from app.api.deps_audit import get_audit_context
    from app.core.config import settings

    monkeypatch.setattr(settings, "audit_enabled", True)
    _override_db(app)
    users = {1: _build_user(user_id=1, username="FirstUser"), 2: _build_user(user_id=2, username="SecondUser")}
    users[2].rol.nombre = "OPERADOR"
    monkeypatch.setattr(deps_auth, "get_user_with_role_and_operador", lambda db, user_id: users.get(user_id))

    async def run():
        ready = asyncio.Event()
        entered = []

        @app.get("/_test/concurrent-actors")
        async def protected(user=Depends(deps_auth.get_current_user), context=Depends(get_audit_context)):
            entered.append(user.id_usuario)
            if len(entered) == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), timeout=5)
            assert context.actor.usuario_id == user.id_usuario
            return context.model_dump(mode="json")

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first, second = await asyncio.gather(*[
                client.get("/_test/concurrent-actors", headers={
                    "Authorization": f"Bearer {create_access_token({'sub': str(user_id)})}",
                }) for user_id in (1, 2)
            ])
        assert first.status_code == second.status_code == 200
        assert first.json()["actor"]["username_snapshot"] == "FirstUser"
        assert second.json()["actor"]["username_snapshot"] == "SecondUser"
        assert first.json()["request_id"] != second.json()["request_id"]

    try:
        asyncio.run(run())
    finally:
        app.dependency_overrides.clear()
