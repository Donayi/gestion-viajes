from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import create_access_token
from app.db.deps import get_db
from app.services.audit_engine import AuditEngine
from app.services.audit_errors import AuditPayloadError


class HttpSession:
    def __init__(self, bind):
        self.bind = bind
        self.transaction = None
        self.is_active = True
        self.new, self.dirty, self.deleted = set(), set(), set()
        self.commit, self.close = Mock(), Mock()
        self.rollback = Mock(side_effect=self._rollback)

    def _rollback(self):
        self.transaction = None

    def get_bind(self):
        return self.bind

    def get_transaction(self):
        return self.transaction

    def in_transaction(self):
        return self.transaction is not None

    def in_nested_transaction(self):
        return False

    def begin(self):
        self.transaction = object()
        return self.transaction


@pytest.fixture
def http_case(app, monkeypatch):
    from app.api import deps_auth, routes_usuarios as routes
    from app.crud import crud_bitacora, crud_usuarios

    monkeypatch.setattr(settings, "audit_enabled", True)
    bind = Mock(spec=Engine)
    db, independent = HttpSession(bind), HttpSession(bind)
    target = SimpleNamespace(
        id_usuario=20, username="target", nombre="Name", apellido="Surname", activo=True,
        id_rol=2, telefono="private-phone", fecha_nacimiento=None,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )
    actor = SimpleNamespace(
        id_usuario=7, username="database-admin", nombre="Admin", apellido="Name", activo=True,
        rol=SimpleNamespace(nombre="ADMIN"), operador=None,
    )
    decode = Mock(wraps=deps_auth.decode_access_token)
    load = Mock(return_value=actor)
    monkeypatch.setattr(deps_auth, "decode_access_token", decode)
    monkeypatch.setattr(deps_auth, "get_user_with_role_and_operador", load)
    app.dependency_overrides[get_db] = lambda: db
    coordinator = AuditEngine(
        config=SimpleNamespace(audit_enabled=True, audit_max_json_bytes=8192),
        session_factory=lambda: independent,
    )
    monkeypatch.setattr(routes, "_audit_engine", lambda: coordinator)
    monkeypatch.setattr(routes, "_prepare_user_response", lambda db, user: routes.UserResponse.model_validate(user))
    monkeypatch.setattr(routes, "get_user_by_id", Mock(return_value=target))
    lock = Mock(return_value=target)
    monkeypatch.setattr(routes, "get_user_by_id_for_update", lock)
    monkeypatch.setattr(routes, "get_user_by_username", Mock(return_value=None))
    monkeypatch.setattr(routes, "role_exists", Mock(return_value=True))
    monkeypatch.setattr(routes, "get_user_referencing_constraints", lambda db: frozenset({("public", "child", "fk_child_user")}))
    create = Mock(return_value=target)
    update = Mock(return_value=target)
    password, deletion = Mock(), Mock()
    monkeypatch.setattr(crud_usuarios, "create_user", create)
    monkeypatch.setattr(crud_usuarios, "update_user_admin", update)
    monkeypatch.setattr(crud_usuarios, "update_user_password", password)
    monkeypatch.setattr(crud_usuarios, "delete_user", deletion)
    audit = Mock(return_value=SimpleNamespace(id_evento=uuid4()))
    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", audit)
    token = create_access_token({"sub": "7", "username": "untrusted-claim", "role": "ADMIN"})
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client, headers={"Authorization": f"Bearer {token}"}, db=db, independent=independent,
            target=target, actor=actor, decode=decode, load=load, coordinator=coordinator,
            create=create, update=update, password=password, deletion=deletion, audit=audit, lock=lock,
            routes=routes,
        )
    app.dependency_overrides.clear()


def request(case, operation):
    if operation == "create":
        return case.client.post("/usuarios/", headers=case.headers, json={
            "username": "new", "nombre": "Name", "apellido": "Surname", "id_rol": 2, "password": "secret-password",
        })
    if operation == "update":
        return case.client.put("/usuarios/20", headers=case.headers, json={"nombre": "New"})
    if operation == "password":
        return case.client.patch("/usuarios/20/password", headers=case.headers, json={"new_password": "secret-password"})
    return case.client.delete("/usuarios/20", headers=case.headers)


@pytest.mark.parametrize("operation,status,action", [
    ("create", 201, "USUARIO_CREADO"), ("update", 200, "USUARIO_ACTUALIZADO"),
    ("password", 200, "USUARIO_CREDENCIAL_CAMBIADA"), ("delete", 204, "USUARIO_ELIMINADO"),
])
def test_success_contract_actor_context_and_single_commit(http_case, operation, status, action):
    case = http_case
    response = request(case, operation)
    assert response.status_code == status
    case.db.commit.assert_called_once()
    case.db.rollback.assert_not_called()
    case.decode.assert_called_once()
    case.load.assert_called_once()
    session, event = case.audit.call_args.args
    assert session is case.db and event.accion == action
    assert event.actor.usuario_id == 7 and event.actor.username_snapshot == "database-admin"
    assert event.request_id is not None and event.ruta_template.startswith("/usuarios")
    if operation == "password":
        assert response.json() == {"message": "Contraseña actualizada correctamente"}
        case.lock.assert_not_called()
    if operation == "delete":
        assert response.content == b""


@pytest.mark.parametrize("operation", ["create", "update", "password", "delete"])
def test_disabled_blocks_every_real_mutation(http_case, operation):
    case = http_case
    case.coordinator.enabled = False
    response = request(case, operation)
    assert response.status_code == 503
    for mutation in (case.create, case.update, case.password, case.deletion, case.audit, case.db.commit):
        mutation.assert_not_called()


@pytest.mark.parametrize("enabled", [True, False])
def test_noop_does_not_open_engine(http_case, monkeypatch, enabled):
    case = http_case
    case.coordinator.enabled = enabled
    operation = Mock(side_effect=AssertionError("no-op must not open engine"))
    monkeypatch.setattr(case.coordinator, "operation", operation)
    response = case.client.put("/usuarios/20", headers=case.headers, json={"nombre": "Name", "telefono": "private-phone"})
    assert response.status_code == 200 and response.json()["updated_at"] == "2026-01-01T00:00:00"
    for mutation in (operation, case.update, case.audit, case.db.commit, case.db.rollback):
        mutation.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "update", "password", "delete"])
def test_commit_failure_never_returns_success(http_case, operation):
    case = http_case
    case.db.commit.side_effect = RuntimeError("private SQL/password/token")
    response = request(case, operation)
    assert response.status_code == 500 and "private" not in response.text
    case.db.close.assert_called_once()
    assert case.audit.call_count == 1  # No automatic FALLIDO for uncertain commit.


@pytest.mark.parametrize("state,known,expected_failed", [("23503", True, True), ("23503", False, False), ("23502", True, False)])
def test_delete_integrity_policy(http_case, state, known, expected_failed):
    case = http_case
    original = Exception("private diagnostic")
    original.sqlstate = state
    original.diag = SimpleNamespace(schema_name="public", table_name="child", constraint_name="fk_child_user" if known else "unknown")
    case.deletion.side_effect = IntegrityError("private SQL", {}, original)
    response = request(case, "delete")
    assert response.status_code == 409
    case.db.rollback.assert_called_once()
    case.db.commit.assert_not_called()
    assert case.audit.call_count == int(expected_failed)
    if expected_failed:
        assert case.audit.call_args.args[0] is case.independent
        assert case.audit.call_args.args[1].resultado.value == "FALLIDO"
        case.independent.commit.assert_called_once()


def test_failed_failure_record_is_not_hidden(http_case):
    case = http_case
    original = Exception("private")
    original.sqlstate = "23503"
    original.diag = SimpleNamespace(schema_name="public", table_name="child", constraint_name="fk_child_user")
    case.deletion.side_effect = IntegrityError("private SQL", {}, original)
    case.audit.side_effect = AuditPayloadError()
    response = request(case, "delete")
    assert response.status_code == 500
    case.independent.rollback.assert_called_once()
    case.independent.close.assert_called_once()


@pytest.mark.parametrize("operation", ["update", "password", "delete"])
def test_missing_target_preserves_404(http_case, operation):
    case = http_case
    case.routes.get_user_by_id.return_value = None
    case.lock.return_value = None
    response = request(case, operation)
    assert response.status_code == 404 and response.json() == {"detail": "Usuario no encontrado"}
    case.audit.assert_not_called()


@pytest.mark.parametrize("role,status", [(None, 401), ("OPERADOR", 403)])
def test_existing_security_denials(http_case, role, status):
    case = http_case
    headers = {} if role is None else case.headers
    if role:
        case.actor.rol.nombre = role
    response = case.client.delete("/usuarios/20", headers=headers)
    assert response.status_code == status
    case.deletion.assert_not_called()
    case.audit.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("validation", ["username", "role"])
def test_existing_validation_contracts(http_case, operation, validation):
    case = http_case
    if validation == "username":
        case.routes.get_user_by_username.return_value = SimpleNamespace(id_usuario=99)
        response = (
            request(case, "create") if operation == "create" else
            case.client.put("/usuarios/20", headers=case.headers, json={"username": "taken"})
        )
        expected = "Ya existe un usuario con ese username" if operation == "create" else "Ya existe otro usuario con ese username"
    else:
        case.routes.role_exists.return_value = False
        response = (
            request(case, "create") if operation == "create" else
            case.client.put("/usuarios/20", headers=case.headers, json={"id_rol": 99})
        )
        expected = "El rol especificado no existe"
    assert response.status_code == 400 and response.json() == {"detail": expected}
    for mutation in (case.create, case.update, case.audit, case.db.commit):
        mutation.assert_not_called()


@pytest.mark.parametrize("path", ["/usuarios/", "/usuarios/20"])
def test_reads_remain_unaudited(http_case, monkeypatch, path):
    case = http_case
    monkeypatch.setattr(case.routes, "get_users", Mock(return_value=[case.target]))
    response = case.client.get(path, headers=case.headers)
    assert response.status_code == 200
    case.audit.assert_not_called()
    case.db.commit.assert_not_called()
    case.lock.assert_not_called()


@pytest.mark.parametrize("invalid_token", [True, False])
def test_invalid_token_or_inactive_actor_cannot_mutate(http_case, invalid_token):
    case = http_case
    headers = {"Authorization": "Bearer invalid-token"} if invalid_token else case.headers
    if not invalid_token:
        case.actor.activo = False
    response = case.client.delete("/usuarios/20", headers=headers)
    assert response.status_code == (401 if invalid_token else 403)
    if invalid_token:
        case.load.assert_not_called()
    case.deletion.assert_not_called()
    case.audit.assert_not_called()
    case.db.commit.assert_not_called()
