"""Real PostgreSQL 16, root Sessions and unique functional fixtures.

The ORM NOT NULL test intentionally expects the inspected mapping's behavior;
if it differs in the real stack, report the discrepancy rather than weakening it.
Audit rows are append-only and are never removed during fixture cleanup.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, event, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker

from app.api import routes_roles as routes
from app.bootstrap import schema_bootstrap
from app.crud import crud_bitacora, crud_roles
from app.models.models import BitacoraEvento, Rol, Usuario
from app.schemas.audit_context import AuditContext
from app.schemas.bitacora import ActorBitacora
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.audit_engine import AuditEngine
from app.services.audit_errors import FailureAuditRecordingError


@pytest.fixture
def case(persistent_test_engine, monkeypatch):
    with persistent_test_engine.begin() as connection:
        assert 160000 <= int(connection.exec_driver_sql("SHOW server_version_num").scalar_one()) < 170000
        schema_bootstrap._install_bitacora_immutability(connection)
    factory = sessionmaker(bind=persistent_test_engine, autoflush=False)
    prefix = "ra_" + uuid4().hex
    owned_roles = set()
    with factory() as setup:
        actor_role = Rol(nombre="ADMIN_" + uuid4().hex, descripcion="Actor role")
        target = Rol(nombre=prefix + "_target", descripcion="Before")
        setup.add_all([actor_role, target])
        setup.flush()
        actor_role_name = actor_role.nombre
        actor = Usuario(username=prefix + "_actor", nombre="Actor", apellido="Audit", activo=True,
                        id_rol=actor_role.id_rol, password_hash="not-used-for-authentication")
        setup.add(actor)
        setup.flush()
        actor_id, target_id = actor.id_usuario, target.id_rol
        owned_roles.update([actor_role.id_rol, target_id])
        setup.commit()
    independent = []

    def independent_factory():
        session = factory()
        independent.append(session)
        return session

    engine = AuditEngine(config=SimpleNamespace(audit_enabled=True, audit_max_json_bytes=8192),
                         session_factory=independent_factory)
    monkeypatch.setattr(routes, "_audit_engine", lambda: engine)

    def context():
        return AuditContext(request_id=uuid4(), correlation_id=uuid4(), actor=ActorBitacora(
            tipo="USUARIO", usuario_id=actor_id, username_snapshot=prefix + "_actor",
            nombre_snapshot="Actor Audit", rol_snapshot=actor_role_name,
        ), metodo_http="PUT", ruta_http="/roles/{role_id}", user_agent="Role audit test")

    ctx = context()

    def call(operation, session, *, update=None, role_id=None, audit_context=None):
        audit_context = audit_context or ctx
        role_id = target_id if role_id is None else role_id
        if operation == "create":
            return routes.create_new_role(RoleCreate(nombre=prefix + "_created", descripcion="Created"),
                                          db=session, audit_context=audit_context)
        if operation == "update":
            return routes.update_existing_role(role_id, update if update is not None else RoleUpdate(descripcion="After"),
                                                db=session, audit_context=audit_context)
        return routes.delete_existing_role(role_id, db=session, audit_context=audit_context)

    def protected_role(name):
        # Existing canonical roles are read only; never delete somebody else's fixture.
        with factory() as setup:
            role = setup.query(Rol).filter(Rol.nombre == name).first()
            if role is None:
                role = Rol(nombre=name, descripcion="Protected test")
                setup.add(role)
                setup.flush()
                owned_roles.add(role.id_rol)
            role_id = role.id_rol
            setup.commit()
            return role_id

    try:
        yield SimpleNamespace(factory=factory, db_engine=persistent_test_engine, engine=engine,
                              prefix=prefix, target_id=target_id, actor_id=actor_id, context=ctx,
                              new_context=context, independent=independent, call=call, protected_role=protected_role)
    finally:
        with persistent_test_engine.begin() as connection:
            connection.execute(Usuario.__table__.delete().where(Usuario.username.in_(
                [prefix + "_actor", prefix + "_dependent"],
            )))
            connection.execute(Rol.__table__.delete().where(
                (Rol.id_rol.in_(owned_roles)) | (Rol.nombre == prefix + "_created"),
            ))


def role_row(case, *, role_id=None, created=False):
    with case.factory() as verification:
        predicate = Rol.nombre == case.prefix + "_created" if created else Rol.id_rol == (
            case.target_id if role_id is None else role_id
        )
        return verification.execute(select(Rol.__table__).where(predicate)).mappings().one_or_none()


def audit_rows(case, context=None):
    with case.factory() as verification:
        return verification.execute(select(BitacoraEvento.__table__).where(
            BitacoraEvento.correlation_id == (context or case.context).correlation_id,
        )).mappings().all()


@pytest.mark.parametrize("operation,action", [("create", "ROL_CREADO"), ("update", "ROL_ACTUALIZADO"), ("delete", "ROL_ELIMINADO")])
def test_joint_commit_same_session_transaction_and_new_session(case, monkeypatch, operation, action):
    commits, captured = [], []
    real_create = crud_bitacora.create_bitacora_evento

    def audited(session, payload):
        assert commits == []
        transaction = session.get_transaction()
        created = real_create(session, payload)
        assert session.get_transaction() is transaction
        captured.append(session)
        return created

    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", audited)
    with case.factory() as functional:
        event.listen(functional, "before_commit", lambda session: commits.append(True))
        result = case.call(operation, functional)
        assert captured == [functional] and commits == [True] and not case.independent
    rows = audit_rows(case)
    assert len(rows) == 1 and rows[0]["accion"] == action and rows[0]["resultado"] == "EXITOSO"
    assert rows[0]["usuario_id"] == case.actor_id and rows[0]["request_id"] == case.context.request_id
    stored = role_row(case, created=operation == "create")
    if operation == "delete":
        assert stored is None and rows[0]["valores_posteriores"] is None
        assert rows[0]["valores_anteriores"] == {"nombre": case.prefix + "_target", "descripcion": "Before"}
    else:
        assert result.id_rol == stored["id_rol"] and result.descripcion == stored["descripcion"]
        if operation == "update":
            assert rows[0]["valores_anteriores"] == {"descripcion": "Before"}
            assert rows[0]["valores_posteriores"] == {"descripcion": "After"}
        else:
            assert rows[0]["valores_anteriores"] is None
            assert rows[0]["valores_posteriores"] == {"nombre": case.prefix + "_created", "descripcion": "Created"}


def fail_real_audit_fk(monkeypatch):
    real_create = crud_bitacora.create_bitacora_evento

    def invalid(session, payload):
        return real_create(session, payload.model_copy(update={"evento_relacionado_id": uuid4()}))

    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", invalid)


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_real_audit_fk_failure_rolls_back_business(case, monkeypatch, operation):
    before = role_row(case)
    fail_real_audit_fk(monkeypatch)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call(operation, functional)
        assert captured.value.status_code == 500
        integrity = captured.value.__cause__.__cause__
        assert isinstance(integrity, IntegrityError) and integrity.orig.sqlstate == "23503"
        assert integrity.orig.diag.table_name == "bitacora_eventos"
    assert role_row(case) == before and role_row(case, created=True) is None and audit_rows(case) == []


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_caller_rollback_before_commit_reverts_both(case, monkeypatch, operation):
    before = role_row(case)
    with case.factory() as functional:
        def rollback_instead_of_commit():
            functional.rollback()
            raise RuntimeError("Intentional test rollback before commit")

        monkeypatch.setattr(functional, "commit", rollback_instead_of_commit)
        with pytest.raises(HTTPException) as captured:
            case.call(operation, functional)
        assert captured.value.status_code == 500
    assert role_row(case) == before and role_row(case, created=True) is None and audit_rows(case) == []


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("fields", [{}, {"descripcion": "Before"}])
def test_noop_no_mutation_flush_commit_or_event(case, monkeypatch, enabled, fields):
    case.engine.enabled = enabled
    statements = []

    def capture_sql(connection, cursor, statement, parameters, context, many):
        statements.append(statement.lstrip().upper())

    monkeypatch.setattr(case.engine, "operation", lambda *args, **kwargs: pytest.fail("No-op opened engine"))
    event.listen(case.db_engine, "before_cursor_execute", capture_sql)
    try:
        with case.factory() as functional:
            monkeypatch.setattr(functional, "flush", lambda *args, **kwargs: pytest.fail("No-op flushed"))
            event.listen(functional, "before_commit", lambda session: pytest.fail("No-op committed"))
            result = case.call("update", functional, update=RoleUpdate(**fields))
            assert result.descripcion == "Before"
    finally:
        event.remove(case.db_engine, "before_cursor_execute", capture_sql)
    assert not any(statement.startswith(("UPDATE", "INSERT", "DELETE")) for statement in statements)
    assert audit_rows(case) == [] and role_row(case)["descripcion"] == "Before"


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_disabled_blocks_real_business_changes(case, operation):
    case.engine.enabled = False
    before = role_row(case)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call(operation, functional)
        assert captured.value.status_code == 503
    assert role_row(case) == before and role_row(case, created=True) is None and audit_rows(case) == []


@pytest.mark.parametrize("operation", ["create", "update"])
def test_unexpected_real_unique_violation_rolls_back_without_failure_event(case, monkeypatch, operation):
    with case.factory() as setup:
        setup.add(Rol(nombre=case.prefix + "_created", descripcion="Existing duplicate"))
        setup.commit()
    before = role_row(case)
    # Bypass only the pre-check to reproduce the database failure a race can produce.
    monkeypatch.setattr(routes, "get_role_by_name", lambda *args: None)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call(operation, functional, update=RoleUpdate(nombre=case.prefix + "_created"))
        assert captured.value.status_code == 500
        assert captured.value.__cause__.orig.sqlstate == "23505"
        assert captured.value.__cause__.orig.diag.table_name == "roles"
    assert role_row(case) == before and role_row(case, created=True)["descripcion"] == "Existing duplicate"
    assert audit_rows(case) == [] and not case.independent


def test_sanitizer_failure_reverts_real_update(case):
    before = role_row(case)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("update", functional, update=RoleUpdate(descripcion="unsafe\ncontrol"))
        assert captured.value.status_code == 500
    assert role_row(case) == before and audit_rows(case) == []


def test_explicit_none_description_is_real_audited_change(case):
    with case.factory() as functional:
        result = case.call("update", functional, update=RoleUpdate(descripcion=None))
    assert result.descripcion is None and role_row(case)["descripcion"] is None
    rows = audit_rows(case)
    assert len(rows) == 1 and rows[0]["valores_anteriores"] == {"descripcion": "Before"}
    assert rows[0]["valores_posteriores"] == {"descripcion": None}


def test_explicit_none_name_not_treated_as_noop(case):
    before = role_row(case)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("update", functional, update=RoleUpdate(nombre=None))
        assert captured.value.status_code == 500
        assert captured.value.__cause__.orig.sqlstate == "23502"
        assert captured.value.__cause__.orig.diag.table_name == "roles"
        assert captured.value.__cause__.orig.diag.column_name == "nombre"
    assert role_row(case) == before and audit_rows(case) == []


@pytest.mark.parametrize("operation,code", [("update", "ROL_BASE_RENOMBRE_PROHIBIDO"), ("delete", "ROL_BASE_ELIMINACION_PROHIBIDA")])
@pytest.mark.parametrize("enabled", [True, False])
def test_real_rejection_independent_and_business_intact(case, operation, code, enabled):
    role_id = case.protected_role("ADMIN")
    before = role_row(case, role_id=role_id)
    case.engine.enabled = enabled
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call(operation, functional, role_id=role_id,
                      update=RoleUpdate(nombre="password=not-stored", descripcion="private-token"))
        assert captured.value.status_code == 400
        assert not functional.in_transaction() and functional.is_active
        if enabled:
            assert len(case.independent) == 1 and case.independent[0] is not functional
    assert role_row(case, role_id=role_id) == before
    rows = audit_rows(case)
    assert len(rows) == int(enabled)
    if enabled:
        assert rows[0]["resultado"] == "RECHAZADO" and rows[0]["error_codigo"] == code
        assert rows[0]["valores_anteriores"] == {"nombre": before["nombre"], "descripcion": before["descripcion"]}
        assert "not-stored" not in repr(rows) and "private-token" not in repr(rows)


def test_actual_orm_role_with_user_observes_not_null(case):
    with case.factory() as setup:
        setup.add(Usuario(username=case.prefix + "_dependent", nombre="Dependent", apellido="Test", activo=True,
                          id_rol=case.target_id, password_hash="not-used"))
        setup.commit()
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("delete", functional)
        assert captured.value.status_code == 409
        integrity = captured.value.__cause__
        assert isinstance(integrity, IntegrityError)
        assert integrity.orig.sqlstate == "23502"
        assert integrity.orig.diag.schema_name == "public"
        assert integrity.orig.diag.table_name == "usuarios"
        assert integrity.orig.diag.column_name == "id_rol"
        assert functional.is_active and not functional.in_transaction()
    assert role_row(case) is not None and audit_rows(case) == [] and not case.independent
    with case.factory() as verification:
        assert verification.execute(select(Usuario.id_rol).where(
            Usuario.username == case.prefix + "_dependent",
        )).scalar_one() == case.target_id


@pytest.fixture
def blocking_fk(case):
    table = Table("ra_fk_" + uuid4().hex, MetaData(),
                  Column("role_id", Integer, ForeignKey(Rol.__table__.c.id_rol), primary_key=True), schema="public")
    table.create(case.db_engine)
    try:
        with case.db_engine.begin() as connection:
            connection.execute(table.insert().values(role_id=case.target_id))
        yield table
    finally:
        table.drop(case.db_engine)


def test_real_recognized_fk_failure_independent_survives(case, blocking_fk):
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("delete", functional)
        assert captured.value.status_code == 409
        integrity = captured.value.__cause__
        assert integrity.orig.sqlstate == "23503"
        assert integrity.orig.diag.schema_name == "public" and integrity.orig.diag.table_name == blocking_fk.name
        assert ("public", blocking_fk.name, integrity.orig.diag.constraint_name) in crud_roles.get_role_referencing_constraints(functional)
        assert len(case.independent) == 1 and case.independent[0] is not functional
    rows = audit_rows(case)
    assert role_row(case) is not None and len(rows) == 1
    assert rows[0]["resultado"] == "FALLIDO" and rows[0]["error_codigo"] == "ROL_ELIMINACION_BLOQUEADA"
    assert rows[0]["error_mensaje"] is None


@pytest.mark.parametrize("outcome", ["failure", "rejection"])
def test_independent_real_audit_failure_rolls_back_own_event(case, blocking_fk, monkeypatch, outcome):
    fail_real_audit_fk(monkeypatch)
    role_id = case.target_id if outcome == "failure" else case.protected_role("ADMIN")
    before = role_row(case, role_id=role_id)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("delete", functional, role_id=role_id)
        assert captured.value.status_code == 500
        assert isinstance(captured.value.__cause__, FailureAuditRecordingError)
        assert len(case.independent) == 1 and case.independent[0] is not functional
        assert not case.independent[0].in_transaction()
    assert role_row(case, role_id=role_id) == before and audit_rows(case) == []


@pytest.mark.parametrize("mutation", ["UPDATE", "DELETE"])
def test_generated_events_remain_append_only(case, mutation):
    with case.factory() as functional:
        case.call("update", functional)
    row = audit_rows(case)[0]
    sql = ("UPDATE public.bitacora_eventos SET accion = 'CHANGE' WHERE id_evento = :id" if mutation == "UPDATE" else
           "DELETE FROM public.bitacora_eventos WHERE id_evento = :id")
    with case.factory() as session:
        with pytest.raises(DBAPIError) as captured:
            session.execute(text(sql), {"id": row["id_evento"]})
        assert captured.value.orig.sqlstate == "55000"
        session.rollback()
    assert audit_rows(case)[0]["accion"] == "ROL_ACTUALIZADO"


@pytest.mark.parametrize("second", ["update", "delete", "noop", "stale_noop"])
def test_concurrent_locked_snapshot_and_strict_noop(case, monkeypatch, second):
    first_locked, second_started, release = Event(), Event(), Event()
    real_lookup = routes.get_role_by_id_for_update
    second_context = case.new_context()

    def lookup(db, role_id):
        if db.info.get("second"):
            second_started.set()
        target = real_lookup(db, role_id)
        if not db.info.get("second"):
            first_locked.set()
            assert release.wait(10)
        return target

    monkeypatch.setattr(routes, "get_role_by_id_for_update", lookup)

    def first():
        with case.factory() as functional:
            case.call("update", functional, update=RoleUpdate(descripcion="Intermediate"))

    def following():
        with case.factory() as functional:
            functional.info["second"] = True
            description = "Intermediate" if second == "noop" else "Before" if second == "stale_noop" else "Final"
            case.call("delete" if second == "delete" else "update", functional,
                      update=RoleUpdate(descripcion=description), audit_context=second_context)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first)
        try:
            assert first_locked.wait(10)
            second_future = pool.submit(following)
            assert second_started.wait(10) and not second_future.done()
        finally:
            release.set()
        first_future.result(timeout=20)
        second_future.result(timeout=20)
    assert len(audit_rows(case)) == 1
    rows = audit_rows(case, second_context)
    if second == "noop":
        assert rows == [] and role_row(case)["descripcion"] == "Intermediate"
    elif second == "delete":
        assert role_row(case) is None and rows[0]["valores_anteriores"]["descripcion"] == "Intermediate"
    else:
        description = "Before" if second == "stale_noop" else "Final"
        assert role_row(case)["descripcion"] == description
        assert rows[0]["valores_anteriores"] == {"descripcion": "Intermediate"}
        assert rows[0]["valores_posteriores"] == {"descripcion": description}
