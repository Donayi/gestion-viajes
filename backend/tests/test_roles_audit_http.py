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
        self.bind, self.transaction = bind, None
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
    from app.api import deps_auth, routes_roles as routes
    from app.crud import crud_bitacora, crud_roles

    monkeypatch.setattr(settings, "audit_enabled", True)
    bind = Mock(spec=Engine)
    db, independent = HttpSession(bind), HttpSession(bind)
    target = SimpleNamespace(id_rol=20, nombre="CUSTOM", descripcion="Existing")
    actor = SimpleNamespace(id_usuario=7, username="database-admin", nombre="Admin", apellido="Name",
                            activo=True, rol=SimpleNamespace(nombre="ADMIN"), operador=None)
    decode = Mock(wraps=deps_auth.decode_access_token)
    load = Mock(return_value=actor)
    monkeypatch.setattr(deps_auth, "decode_access_token", decode)
    monkeypatch.setattr(deps_auth, "get_user_with_role_and_operador", load)
    app.dependency_overrides[get_db] = lambda: db
    engine = AuditEngine(config=SimpleNamespace(audit_enabled=True, audit_max_json_bytes=8192),
                         session_factory=lambda: independent)
    monkeypatch.setattr(routes, "_audit_engine", lambda: engine)
    lock = Mock(return_value=target)
    monkeypatch.setattr(routes, "get_role_by_id_for_update", lock)
    monkeypatch.setattr(routes, "get_role_by_id", Mock(return_value=target))
    monkeypatch.setattr(routes, "get_role_by_name", Mock(return_value=None))
    monkeypatch.setattr(routes, "get_roles", Mock(return_value=[target]))
    monkeypatch.setattr(routes, "get_role_referencing_constraints", lambda db: frozenset({("public", "child", "fk_role")}))
    create = Mock(return_value=target)

    def update(db, target, payload):
        for field in payload.model_fields_set:
            setattr(target, field, getattr(payload, field))
        return target

    mutation = Mock(side_effect=update)
    deletion = Mock()
    monkeypatch.setattr(crud_roles, "create_role", create)
    monkeypatch.setattr(crud_roles, "update_role", mutation)
    monkeypatch.setattr(crud_roles, "delete_role", deletion)
    audit = Mock(return_value=SimpleNamespace(id_evento=uuid4()))
    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", audit)
    token = create_access_token({"sub": "7", "username": "untrusted-claim", "role": "ADMIN"})
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, headers={"Authorization": f"Bearer {token}"}, db=db,
                                  independent=independent, target=target, actor=actor, decode=decode, load=load,
                                  engine=engine, create=create, update=mutation, deletion=deletion,
                                  audit=audit, lock=lock, routes=routes)
    finally:
        app.dependency_overrides.clear()


def request(case, operation):
    if operation == "create":
        return case.client.post("/roles/", headers=case.headers, json={"nombre": "New", "descripcion": "Safe"})
    if operation == "update":
        return case.client.put("/roles/20", headers=case.headers, json={"descripcion": "Changed"})
    return case.client.delete("/roles/20", headers=case.headers)


@pytest.mark.parametrize("operation,status,action", [
    ("create", 201, "ROL_CREADO"), ("update", 200, "ROL_ACTUALIZADO"), ("delete", 204, "ROL_ELIMINADO"),
])
@pytest.mark.parametrize("admin", ["ADMIN", "ADMIN_CUSTOM"])
def test_success_actor_and_one_commit(http_case, operation, status, action, admin):
    case = http_case
    case.actor.rol.nombre = admin
    response = request(case, operation)
    assert response.status_code == status
    case.db.commit.assert_called_once()
    case.db.rollback.assert_not_called()
    case.decode.assert_called_once()
    case.load.assert_called_once()
    session, event = case.audit.call_args.args
    assert session is case.db and event.accion == action
    assert event.actor.username_snapshot == "database-admin" and event.actor.rol_snapshot == admin
    assert event.request_id is not None and event.categoria.value == "SEGURIDAD"
    if operation == "create":
        case.lock.assert_not_called()
    if operation == "delete":
        assert response.content == b""


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("payload", [{}, {"nombre": "CUSTOM", "descripcion": "Existing"}])
def test_noop_without_engine(http_case, monkeypatch, enabled, payload):
    case = http_case
    case.engine.enabled = enabled
    opened = Mock(side_effect=AssertionError("No-op opened audit operation"))
    monkeypatch.setattr(case.engine, "operation", opened)
    response = case.client.put("/roles/20", headers=case.headers, json=payload)
    assert response.status_code == 200
    for called in (opened, case.update, case.audit, case.db.commit, case.db.rollback):
        called.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_disabled_blocks_before_mutation(http_case, operation):
    case = http_case
    case.engine.enabled = False
    assert request(case, operation).status_code == 503
    for called in (case.create, case.update, case.deletion, case.audit, case.db.commit):
        called.assert_not_called()


@pytest.mark.parametrize("base", ["ADMIN", "OPERADOR", "MANTENIMIENTO"])
@pytest.mark.parametrize("operation,action,code", [
    ("update", "ROL_ACTUALIZADO", "ROL_BASE_RENOMBRE_PROHIBIDO"),
    ("delete", "ROL_ELIMINADO", "ROL_BASE_ELIMINACION_PROHIBIDA"),
])
@pytest.mark.parametrize("enabled", [True, False])
def test_protected_rejection_and_disabled_400(http_case, base, operation, action, code, enabled):
    case = http_case
    case.target.nombre = base
    case.engine.enabled = enabled
    response = (
        case.client.put("/roles/20", headers=case.headers, json={"nombre": "password=DO_NOT_STORE", "descripcion": "private-token"})
        if operation == "update" else request(case, operation)
    )
    assert response.status_code == 400
    case.db.rollback.assert_called_once()
    case.db.commit.assert_not_called()
    case.update.assert_not_called()
    case.deletion.assert_not_called()
    assert case.audit.call_count == int(enabled)
    if enabled:
        session, event = case.audit.call_args.args
        assert session is case.independent and event.resultado.value == "RECHAZADO"
        assert event.accion == action and event.error_codigo == code
        assert event.valores_anteriores == {"nombre": base, "descripcion": "Existing"}
        assert "DO_NOT_STORE" not in event.model_dump_json() and "private-token" not in event.model_dump_json()
        case.independent.commit.assert_called_once()


@pytest.mark.parametrize("name", ["admin", " ADMIN "])
def test_normalized_equivalent_base_name_is_real_change(http_case, name):
    case = http_case
    case.target.nombre = "ADMIN"
    response = case.client.put("/roles/20", headers=case.headers, json={"nombre": name})
    assert response.status_code == 200
    event = case.audit.call_args.args[1]
    assert event.valores_anteriores == {"nombre": "ADMIN"} and event.valores_posteriores == {"nombre": name}


def test_protected_description_is_editable(http_case):
    http_case.target.nombre = "ADMIN"
    assert request(http_case, "update").status_code == 200
    assert http_case.audit.call_args.args[1].resultado.value == "EXITOSO"


@pytest.mark.parametrize("case_name,status", [("missing_auth", 401), ("operator", 403), ("missing_role", 404), ("invalid_id", 422)])
def test_routine_errors_without_audit(http_case, case_name, status):
    case = http_case
    if case_name == "operator":
        case.actor.rol.nombre = "OPERADOR"
    if case_name == "missing_role":
        case.lock.return_value = None
    response = case.client.delete("/roles/not-an-id" if case_name == "invalid_id" else "/roles/20",
                                  headers={} if case_name == "missing_auth" else case.headers)
    assert response.status_code == status
    case.audit.assert_not_called()
    case.deletion.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "update"])
def test_duplicate_is_not_audit_event(http_case, operation):
    case = http_case
    case.routes.get_role_by_name.return_value = SimpleNamespace(id_rol=99)
    response = (request(case, "create") if operation == "create" else
                case.client.put("/roles/20", headers=case.headers, json={"nombre": "Taken"}))
    assert response.status_code == 400
    case.audit.assert_not_called()
    case.db.commit.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_required_audit_failure_rolls_back(http_case, operation):
    case = http_case
    case.audit.side_effect = AuditPayloadError()
    assert request(case, operation).status_code == 500
    case.db.rollback.assert_called_once()
    case.db.commit.assert_not_called()
    case.independent.commit.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_commit_failure_not_success_or_failure_event(http_case, operation):
    case = http_case
    case.db.commit.side_effect = RuntimeError("private SQL/token")
    response = request(case, operation)
    assert response.status_code == 500 and "private" not in response.text
    assert case.audit.call_count == 1 and case.audit.call_args.args[1].resultado.value == "EXITOSO"
    case.db.close.assert_called_once()


def test_rejection_audit_failure_visible(http_case):
    case = http_case
    case.target.nombre = "ADMIN"
    case.audit.side_effect = AuditPayloadError()
    assert request(case, "delete").status_code == 500
    case.independent.rollback.assert_called_once()
    case.independent.close.assert_called_once()


@pytest.mark.parametrize("state,known,failed", [("23503", True, True), ("23503", False, False), ("23502", True, False)])
def test_delete_integrity_classification(http_case, state, known, failed):
    case = http_case
    orig = Exception("private")
    orig.sqlstate = state
    orig.diag = SimpleNamespace(schema_name="public", table_name="usuarios" if state == "23502" else "child", column_name="id_rol",
                                constraint_name="fk_role" if known else "unknown")
    case.deletion.side_effect = IntegrityError("private SQL", {}, orig)
    assert request(case, "delete").status_code == 409
    case.db.rollback.assert_called_once()
    assert case.audit.call_count == int(failed)
    if failed:
        assert case.audit.call_args.args[0] is case.independent
        assert case.audit.call_args.args[1].error_codigo == "ROL_ELIMINACION_BLOQUEADA"


@pytest.mark.parametrize("path", ["/roles/", "/roles/20"])
def test_reads_are_unaudited(http_case, path):
    assert http_case.client.get(path, headers=http_case.headers).status_code == 200
    http_case.audit.assert_not_called()
    http_case.db.commit.assert_not_called()
