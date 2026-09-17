"""Real root commits in db_test; committed audit rows are intentionally append-only.

Every verification filters this test's UUIDs. Only the unique controlled business
table is dropped. No CREATE DATABASE, audit DELETE or disabled trigger.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, Column, MetaData, String, Table, event, inspect, select, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import registry, sessionmaker

from app.crud import crud_bitacora
from app.models.models import BitacoraEvento
from app.services.audit_context import build_system_audit_context
from app.services.audit_engine import AuditEngine
from app.services.audit_errors import (
    AuditEngineError, AuditPayloadError, AuditPersistenceError, AuditTransactionError, FailureAuditRecordingError,
)


@pytest.fixture(scope="module")
def business_table(persistent_test_engine):
    from app.bootstrap import schema_bootstrap

    # persistent_test_engine validates db_test/logistica_test credentials in conftest.
    with persistent_test_engine.begin() as connection:
        version = int(connection.exec_driver_sql("SHOW server_version_num").scalar_one())
        assert 160000 <= version < 170000
        schema_bootstrap._install_bitacora_immutability(connection)
    suffix = uuid4().hex
    table = Table(
        f"audit_engine_test_{suffix}", MetaData(),
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("value", String(100), nullable=False),
        CheckConstraint("value <> 'INVALID'", name=f"ck_audit_business_{suffix}"),
        schema="public",
    )
    table.create(persistent_test_engine)
    try:
        yield table
    finally:
        table.drop(persistent_test_engine)


@pytest.fixture
def environment(persistent_test_engine, business_table):
    factory = sessionmaker(bind=persistent_test_engine, autoflush=False)
    independent_sessions = []

    def independent_factory():
        session = factory()
        independent_sessions.append(session)
        return session

    engine = AuditEngine(
        config=SimpleNamespace(audit_enabled=True, audit_max_json_bytes=8192),
        session_factory=independent_factory,
    )
    return engine, factory, business_table, independent_sessions


def details(entity_id):
    return dict(
        categoria="FUNCIONAL", modulo=f"ENGINE_{uuid4().hex.upper()}", accion="CREAR",
        entidad_tipo="TEST_ENGINE", entidad_id=str(entity_id), datos_evento={"value": "safe"},
    )


def stored(factory, table, business_id, context):
    # New Session, root transaction, direct SQL. Never Session.get/identity map.
    with factory() as verification:
        business = verification.execute(select(table.c.id).where(table.c.id == business_id)).scalars().all()
        events = verification.execute(select(
            BitacoraEvento.id_evento, BitacoraEvento.resultado, BitacoraEvento.entidad_id,
        ).where(BitacoraEvento.correlation_id == context.correlation_id)).all()
        return business, events


def test_success_same_session_same_transaction_no_hidden_commit(environment, monkeypatch):
    engine, factory, table, independent = environment
    context = build_system_audit_context()
    business_id = uuid4()
    captured = []
    commits = []
    real_create = crud_bitacora.create_bitacora_evento

    def create(session, payload):
        captured.append((session, session.get_transaction()))
        return real_create(session, payload)

    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", create)
    with factory() as functional:
        event.listen(functional, "before_commit", lambda session: commits.append(True))
        with engine.operation(functional, context) as operation:
            functional.execute(table.insert().values(id=business_id, value="safe"))
            result = operation.success(**details(business_id))
            assert captured == [(functional, operation.transaction)]
            assert not commits and not independent
            assert not result.committed
            assert stored(factory, table, business_id, context) == ([], [])
            functional.commit()
        assert len(commits) == 1
    business, records = stored(factory, table, business_id, context)
    assert business == [business_id]
    assert [(record.id_evento, record.resultado) for record in records] == [(result.event_id, "EXITOSO")]


def test_caller_rollback_removes_business_and_success(environment):
    engine, factory, table, independent = environment
    context, business_id = build_system_audit_context(), uuid4()
    with factory() as functional:
        operation = engine.operation(functional, context)
        functional.execute(table.insert().values(id=business_id, value="safe"))
        operation.success(**details(business_id))
        functional.rollback()
    assert stored(factory, table, business_id, context) == ([], [])
    assert not independent


@pytest.mark.parametrize("defect", ["payload", "contract", "fk", "check"])
def test_failed_success_audit_rollback_removes_both(environment, defect, monkeypatch):
    engine, factory, table, independent = environment
    context, business_id = build_system_audit_context(), uuid4()
    payload = details(business_id)
    if defect == "payload":
        payload["datos_evento"] = {"password": "secret"}
    elif defect == "contract":
        payload["modulo"] = "invalid-lowercase"
    elif defect == "fk":
        payload["evento_relacionado_id"] = uuid4()
    else:
        # Fault injection only: real CRUD and real PostgreSQL enforce the CHECK.
        real_create = crud_bitacora.create_bitacora_evento

        def corrupt_before_insert(session, event_input):
            return real_create(session, event_input.model_copy(update={"schema_version": 0}))

        monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", corrupt_before_insert)
    with factory() as functional:
        operation = engine.operation(functional, context)
        functional.execute(table.insert().values(id=business_id, value="safe"))
        with pytest.raises(AuditPersistenceError if defect in {"fk", "check"} else AuditPayloadError) as captured:
            operation.success(**payload)
        if defect == "fk":
            assert captured.value.__cause__.orig.sqlstate == "23503"
            assert captured.value.__cause__.orig.diag.table_name == "bitacora_eventos"
            expected_fk = next(fk["name"] for fk in inspect(functional.get_bind()).get_foreign_keys(
                "bitacora_eventos", schema="public"
            ) if fk["constrained_columns"] == ["evento_relacionado_id"])
            assert captured.value.__cause__.orig.diag.constraint_name == expected_fk
        elif defect == "check":
            assert captured.value.__cause__.orig.sqlstate == "23514"
            assert captured.value.__cause__.orig.diag.constraint_name == "ck_bitacora_eventos_schema_version"
        assert not operation.completed
        functional.rollback()
    assert stored(factory, table, business_id, context) == ([], [])
    assert not independent


def test_real_business_check_failure_then_surviving_failure_audit(environment):
    engine, factory, table, independent = environment
    context, business_id = build_system_audit_context(), uuid4()
    with factory() as functional:
        operation = engine.operation(functional, context)
        functional.execute(table.insert().values(id=business_id, value="safe"))
        with pytest.raises(IntegrityError) as captured:
            functional.execute(table.insert().values(id=uuid4(), value="INVALID"))
        assert captured.value.orig.sqlstate == "23514"
        assert captured.value.orig.diag.constraint_name.startswith("ck_audit_business_")
        with pytest.raises(AuditTransactionError):
            operation.failure(captured.value, **details(business_id), error_codigo="BUSINESS_FAILED")
        assert not independent
        operation.rollback_business()
        result = operation.failure(captured.value, **details(business_id), error_codigo="BUSINESS_FAILED")
        assert len(independent) == 1
        assert independent[0] is not functional
        assert result.committed
        # No commit on the functional Session: closing it cannot erase failure audit.
    business, records = stored(factory, table, business_id, context)
    assert business == []
    assert [(record.id_evento, record.resultado) for record in records] == [(result.event_id, "FALLIDO")]


def test_business_error_in_audit_flush_not_mislabeled(environment):
    engine, factory, table, independent = environment
    context, business_id = build_system_audit_context(), uuid4()
    mappings = registry()

    class ControlledBusiness:
        pass

    mappings.map_imperatively(ControlledBusiness, table)
    try:
        with factory() as functional:
            operation = engine.operation(functional, context)
            functional.add(ControlledBusiness(id=business_id, value="INVALID"))
            with pytest.raises(AuditEngineError) as captured:
                operation.success(**details(business_id))
            assert type(captured.value) is AuditEngineError
            assert isinstance(captured.value.__cause__, IntegrityError)
            assert captured.value.__cause__.orig.sqlstate == "23514"
            assert captured.value.__cause__.orig.diag.table_name == table.name
            operation.rollback_business()
    finally:
        mappings.dispose()
    assert stored(factory, table, business_id, context) == ([], [])


def test_failure_audit_fk_error_visible_business_stays_rolled_back(environment):
    engine, factory, table, independent = environment
    context, business_id = build_system_audit_context(), uuid4()
    business_error = RuntimeError("known pre-commit business failure")
    with factory() as functional:
        operation = engine.operation(functional, context)
        functional.execute(table.insert().values(id=business_id, value="safe"))
        operation.rollback_business()
        with pytest.raises(FailureAuditRecordingError) as captured:
            operation.failure(
                business_error, **details(business_id), error_codigo="BUSINESS_FAILED",
                evento_relacionado_id=uuid4(),
            )
        assert captured.value.business_error is business_error
        assert isinstance(captured.value.__cause__, AuditPersistenceError)
        assert captured.value.__cause__.__cause__.orig.sqlstate == "23503"
        assert independent[0] is not functional
    assert stored(factory, table, business_id, context) == ([], [])


def test_explicit_rejected_persists_without_business(environment):
    engine, factory, table, independent = environment
    context, business_id = build_system_audit_context(), uuid4()
    with factory() as functional:
        result = engine.record_rejected(
            context, functional_session=functional, **details(business_id), error_codigo="DENIED",
        )
        assert independent[0] is not functional
    business, records = stored(factory, table, business_id, context)
    assert business == []
    assert [(record.id_evento, record.resultado) for record in records] == [(result.event_id, "RECHAZADO")]


def test_concurrent_operations_do_not_mix_context_or_entity(environment):
    engine, factory, table, independent = environment
    barrier = Barrier(2)
    pairs = [(uuid4(), build_system_audit_context()) for _ in range(2)]

    def run(pair):
        business_id, context = pair
        with factory() as functional:
            with engine.operation(functional, context) as operation:
                functional.execute(table.insert().values(id=business_id, value="safe"))
                barrier.wait(timeout=10)
                result = operation.success(**details(business_id))
                functional.commit()
                return result.event_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        identifiers = list(pool.map(run, pairs))
    assert len(set(identifiers)) == 2
    for (business_id, context), event_id in zip(pairs, identifiers):
        business, records = stored(factory, table, business_id, context)
        assert business == [business_id]
        assert [(row.id_evento, row.resultado, row.entidad_id) for row in records] == [(event_id, "EXITOSO", str(business_id))]
    assert not independent


@pytest.mark.parametrize("mutation", ["update", "delete"])
def test_committed_events_remain_immutable(environment, mutation):
    engine, factory, table, independent = environment
    context, business_id = build_system_audit_context(), uuid4()
    result = engine.record_rejected(
        context, functional_session=None, **details(business_id), error_codigo="DENIED",
    )
    statement = (
        "UPDATE public.bitacora_eventos SET accion = 'CAMBIAR' WHERE id_evento = :id"
        if mutation == "update" else "DELETE FROM public.bitacora_eventos WHERE id_evento = :id"
    )
    with factory() as session:
        with pytest.raises(DBAPIError) as captured:
            session.execute(text(statement), {"id": result.event_id})
        assert captured.value.orig.sqlstate == "55000"
        session.rollback()
        assert session.execute(select(BitacoraEvento.accion).where(BitacoraEvento.id_evento == result.event_id)).scalar_one() == "CREAR"
    assert stored(factory, table, business_id, context)[1][0].resultado == "RECHAZADO"
