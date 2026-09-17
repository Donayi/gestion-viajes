from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.schemas.audit_context import AuditContext
from app.schemas.bitacora import ActorBitacora
from app.services.audit_context import build_system_audit_context
from app.services.audit_engine import AuditEngine, AuditRequirement
from app.services.audit_errors import (
    AuditEngineError, AuditDisabledError, AuditPayloadError, AuditPersistenceError,
    AuditTransactionError, FailureAuditRecordingError,
)


DATA = dict(categoria="FUNCIONAL", modulo="PRUEBA", accion="CREAR")


class FakeSession:
    def __init__(self, bind, active=False):
        self.bind = bind
        self.transaction = object() if active else None
        self.is_active = True
        self.new = set()
        self.dirty = set()
        self.deleted = set()
        self.commit = Mock()
        self.close = Mock()
        self.rollback = Mock(side_effect=self._rollback)

    def _rollback(self):
        self.transaction = None
        self.new.clear()
        self.dirty.clear()
        self.deleted.clear()

    def get_bind(self):
        return self.bind

    def get_transaction(self):
        return self.transaction

    def begin(self):
        self.transaction = object()
        return self.transaction

    def in_transaction(self):
        return self.transaction is not None

    def in_nested_transaction(self):
        return False


@pytest.fixture
def setup_engine(monkeypatch):
    from app.crud import crud_bitacora

    bind = Mock(spec=Engine)
    functional = FakeSession(bind, active=True)
    independent = FakeSession(bind)
    factory = Mock(return_value=independent)
    create = Mock(return_value=SimpleNamespace(id_evento=uuid4()))
    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", create)
    engine = AuditEngine(
        config=SimpleNamespace(audit_enabled=True, audit_max_json_bytes=8192),
        session_factory=factory,
    )
    return engine, functional, independent, factory, create


def test_required_disabled_is_rejected_before_mutation(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    engine.enabled = False
    mutation = Mock()
    with pytest.raises(AuditDisabledError):
        with engine.operation(functional, build_system_audit_context()):
            mutation()
    mutation.assert_not_called()
    factory.assert_not_called()
    create.assert_not_called()


def test_optional_disabled_returns_explicit_skip(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    engine.enabled = False
    with engine.operation(functional, build_system_audit_context(), requirement=AuditRequirement.OPTIONAL) as operation:
        result = operation.success(**DATA)
    assert result.skipped and result.event_id is None and not result.committed
    factory.assert_not_called()
    create.assert_not_called()
    functional.commit.assert_not_called()
    functional.rollback.assert_not_called()
    assert engine.record_rejected(
        build_system_audit_context(), functional_session=None, requirement=AuditRequirement.OPTIONAL,
    ).skipped


def test_disabled_optional_does_not_copy_or_validate_auditable_context(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    engine.enabled = False
    with engine.operation(functional, None, requirement=AuditRequirement.OPTIONAL) as operation:
        assert operation.context is None
        assert operation.success().skipped
    factory.assert_not_called()


def test_success_same_session_no_commit_rollback_or_factory(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    with engine.operation(functional, build_system_audit_context()) as operation:
        result = operation.success(**DATA)
    assert operation.completed
    assert create.call_args.args[0] is functional
    assert result.event_id == create.return_value.id_evento
    assert not result.committed and not result.skipped
    functional.commit.assert_not_called()
    functional.rollback.assert_not_called()
    factory.assert_not_called()


def test_missing_success_is_not_considered_completed(setup_engine):
    engine, functional, *_ = setup_engine
    with pytest.raises(AuditTransactionError):
        with engine.operation(functional, build_system_audit_context()):
            pass
    functional.commit.assert_not_called()
    functional.rollback.assert_not_called()


def test_payload_error_keeps_operation_incomplete_and_preserves_cause(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    operation = engine.operation(functional, build_system_audit_context())
    with pytest.raises(AuditPayloadError) as captured:
        operation.success(**DATA, entidad_tipo="PRUEBA", entidad_id=None)
    assert captured.value.__cause__ is not None
    assert not operation.completed
    create.assert_not_called()
    functional.commit.assert_not_called()
    functional.rollback.assert_not_called()


def test_failure_requires_explicit_rollback_and_commits_independently(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    operation = engine.operation(functional, build_system_audit_context())
    error = ValueError("business secret")
    with pytest.raises(AuditTransactionError):
        operation.failure(error, **DATA, error_codigo="BUSINESS_FAILED")
    factory.assert_not_called()
    operation.rollback_business()
    result = operation.failure(error, **DATA, error_codigo="BUSINESS_FAILED")
    factory.assert_called_once()
    assert create.call_args.args[0] is independent
    assert independent is not functional
    assert create.call_args.args[1].resultado.value == "FALLIDO"
    independent.commit.assert_called_once()
    independent.close.assert_called_once()
    independent.rollback.assert_not_called()
    functional.commit.assert_not_called()
    assert result.committed


def test_failed_failure_record_rolls_back_closes_and_preserves_both_errors(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    business_error = ValueError("password=business-secret")
    audit_error = RuntimeError("token=audit-secret")
    operation = engine.operation(functional, build_system_audit_context())
    operation.rollback_business()
    create.side_effect = audit_error
    with pytest.raises(FailureAuditRecordingError) as captured:
        operation.failure(business_error, **DATA, error_codigo="BUSINESS_FAILED")
    assert type(captured.value.__cause__) is AuditEngineError
    assert captured.value.__cause__.__cause__ is audit_error
    assert captured.value.business_error is business_error
    assert "secret" not in str(captured.value)
    independent.rollback.assert_called_once()
    independent.close.assert_called_once()
    independent.commit.assert_not_called()
    assert not operation.completed


def test_rejected_explicit_uses_independent_session(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    with pytest.raises(AuditTransactionError):
        engine.record_rejected(build_system_audit_context(), functional_session=functional, **DATA, error_codigo="DENIED")
    functional.rollback()
    result = engine.record_rejected(build_system_audit_context(), functional_session=functional, **DATA, error_codigo="DENIED")
    assert create.call_args.args[0] is independent
    assert create.call_args.args[1].resultado.value == "RECHAZADO"
    assert result.committed
    independent.commit.assert_called_once()
    independent.close.assert_called_once()


@pytest.mark.parametrize("status", [401, 403, 404, 422, 500])
def test_http_exception_is_not_automatically_audited(setup_engine, status):
    engine, functional, independent, factory, create = setup_engine
    original = HTTPException(status, "private-detail")
    with pytest.raises(HTTPException) as captured:
        with engine.operation(functional, build_system_audit_context()):
            raise original
    assert captured.value is original
    create.assert_not_called()
    factory.assert_not_called()
    functional.rollback.assert_not_called()


@pytest.mark.parametrize("audit_table", [True, False, None])
def test_only_identified_audit_constraint_is_classified(setup_engine, audit_table):
    engine, functional, independent, factory, create = setup_engine
    original = Exception("secret-parameters")
    original.diag = SimpleNamespace(
        schema_name="public", table_name="bitacora_eventos" if audit_table else "business" if audit_table is False else None,
        constraint_name="ck_constraint",
    )
    error = IntegrityError("private-sql", {"password": "private-value"}, original)
    create.side_effect = error
    operation = engine.operation(functional, build_system_audit_context())
    with pytest.raises(AuditPersistenceError if audit_table else AuditEngineError) as captured:
        operation.success(**DATA)
    assert captured.value.__cause__ is error
    if not audit_table:
        assert type(captured.value) is AuditEngineError
    assert "private" not in str(captured.value)
    assert not operation.completed


def test_factory_cannot_reuse_functional_session(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    factory.return_value = functional
    operation = engine.operation(functional, build_system_audit_context())
    operation.rollback_business()
    with pytest.raises(FailureAuditRecordingError) as captured:
        operation.failure(ValueError(), **DATA, error_codigo="BUSINESS_FAILED")
    assert isinstance(captured.value.__cause__, AuditTransactionError)
    functional.close.assert_not_called()
    functional.commit.assert_not_called()
    assert functional.rollback.call_count == 1


def test_nested_transaction_cannot_hold_required_success(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    operation = engine.operation(functional, build_system_audit_context())
    functional.in_nested_transaction = lambda: True
    with pytest.raises(AuditTransactionError):
        operation.success(**DATA)
    create.assert_not_called()


def test_new_functional_transaction_after_rollback_blocks_failure(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    operation = engine.operation(functional, build_system_audit_context())
    operation.rollback_business()
    functional.begin()
    with pytest.raises(AuditTransactionError):
        operation.failure(ValueError(), **DATA, error_codigo="BUSINESS_FAILED")
    factory.assert_not_called()


def test_independent_cleanup_failure_does_not_hide_original_error(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    operation = engine.operation(functional, build_system_audit_context())
    operation.rollback_business()
    original = RuntimeError("original-private-error")
    cleanup = RuntimeError("private-cleanup-error")
    create.side_effect = original
    independent.rollback.side_effect = cleanup
    with pytest.raises(FailureAuditRecordingError) as captured:
        operation.failure(ValueError(), **DATA, error_codigo="BUSINESS_FAILED")
    assert captured.value.__cause__.__cause__ is original
    assert captured.value.cleanup_errors == (cleanup,)
    independent.close.assert_called_once()
    assert "private" not in str(captured.value)


def test_failed_independent_attempt_is_not_automatically_retried(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    operation = engine.operation(functional, build_system_audit_context())
    operation.rollback_business()
    independent.commit.side_effect = RuntimeError("uncertain independent commit")
    with pytest.raises(FailureAuditRecordingError):
        operation.failure(ValueError(), **DATA, error_codigo="BUSINESS_FAILED")
    with pytest.raises(AuditTransactionError):
        operation.failure(ValueError(), **DATA, error_codigo="BUSINESS_FAILED")
    factory.assert_called_once()


def test_ended_committed_transaction_is_not_rollback_evidence(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    operation = engine.operation(functional, build_system_audit_context())
    functional.transaction = None  # External commit ending a root must not authorize failure.
    with pytest.raises(AuditTransactionError):
        operation.failure(ValueError(), **DATA, error_codigo="BUSINESS_FAILED")
    with pytest.raises(AuditTransactionError):
        operation.rollback_business()
    factory.assert_not_called()


def test_context_copied_revalidated_and_existing_http_fields_mapped(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    context = AuditContext(
        request_id=uuid4(), actor=ActorBitacora(
            tipo="USUARIO", usuario_id=7, username_snapshot="DatabaseUser",
            nombre_snapshot="User Name", rol_snapshot="ADMIN",
        ), metodo_http="POST", ruta_http="/items/{id}", user_agent="Browser\r\n v1",
    )
    operation = engine.operation(functional, context)
    context.actor.username_snapshot = "changed-later"
    operation.success(**DATA)
    event = create.call_args.args[1]
    assert event.actor.username_snapshot == "DatabaseUser"
    assert event.actor_username_normalizado == "DatabaseUser"
    assert event.ruta_template == "/items/{id}"
    assert event.metodo_http == "POST"
    assert event.user_agent == "Browser v1"
    assert "codigo_http" not in event.model_dump()


@pytest.mark.parametrize("field", ["entidad_id", "error_codigo"])
def test_non_json_event_fields_reject_controls(setup_engine, field):
    engine, functional, independent, factory, create = setup_engine
    payload = dict(DATA, entidad_tipo="PRUEBA", entidad_id="record")
    payload[field] = "private\x00value"
    with pytest.raises(AuditPayloadError):
        engine.operation(functional, build_system_audit_context()).success(**payload)
    create.assert_not_called()


def test_snapshot_controls_rejected_without_changing_auth_or_storage(setup_engine):
    engine, functional, independent, factory, create = setup_engine
    context = AuditContext(request_id=uuid4(), actor=ActorBitacora(
        tipo="USUARIO", usuario_id=1, username_snapshot="user", nombre_snapshot="User\nName",
        rol_snapshot="ADMIN",
    ))
    with pytest.raises(AuditPayloadError):
        engine.operation(functional, context)
    create.assert_not_called()


@pytest.mark.parametrize("field", ["categoria", "modulo", "accion", "entidad_tipo", "entidad_id", "error_codigo"])
def test_controls_rejected_before_contract_can_strip_them(setup_engine, field):
    engine, functional, independent, factory, create = setup_engine
    payload = dict(DATA, entidad_tipo="PRUEBA", entidad_id="record", error_codigo="CODE")
    payload[field] += "\n"
    with pytest.raises(AuditPayloadError):
        engine.operation(functional, build_system_audit_context()).success(**payload)
    create.assert_not_called()
