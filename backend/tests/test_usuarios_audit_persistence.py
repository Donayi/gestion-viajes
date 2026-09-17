"""PostgreSQL 16 root transactions; audit rows are never deleted for cleanup."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from uuid import uuid4
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.api import routes_usuarios as routes
from app.bootstrap import schema_bootstrap
from app.core.security import get_password_hash, verify_password
from app.crud import crud_bitacora
from app.models.models import BitacoraEvento, Operador, Rol, Usuario
from app.schemas.audit_context import AuditContext
from app.schemas.bitacora import ActorBitacora
from app.schemas.user import UserAdminUpdate, UserCreate, UserPasswordUpdate
from app.services.audit_engine import AuditEngine
from app.services.audit_errors import AuditPayloadError


@pytest.fixture
def case(persistent_test_engine, monkeypatch):
    with persistent_test_engine.begin() as connection:
        assert 160000 <= int(connection.exec_driver_sql("SHOW server_version_num").scalar_one()) < 170000
        schema_bootstrap._install_bitacora_immutability(connection)
    factory = sessionmaker(bind=persistent_test_engine, autoflush=False)
    prefix = "ua_" + uuid4().hex
    role_name = "ADMIN_" + uuid4().hex
    initial_hash = get_password_hash("initial-password")
    with factory() as setup:
        role = Rol(nombre=role_name, descripcion="Audit test")
        setup.add(role)
        setup.flush()
        role_id = role.id_rol
        actor = Usuario(username=prefix + "_actor", nombre="Actor", apellido="Audit", activo=True,
                        id_rol=role_id, password_hash=initial_hash)
        target = Usuario(username=prefix + "_target", nombre="Before", apellido="Surname", activo=True,
                         id_rol=role_id, password_hash=initial_hash, telefono="private-phone")
        setup.add_all([actor, target])
        setup.flush()
        actor_id, target_id = actor.id_usuario, target.id_usuario
        setup.commit()
    independent = []

    def independent_factory():
        session = factory()
        independent.append(session)
        return session

    engine = AuditEngine(config=SimpleNamespace(audit_enabled=True, audit_max_json_bytes=8192), session_factory=independent_factory)
    monkeypatch.setattr(routes, "_audit_engine", lambda: engine)

    def context():
        return AuditContext(
            request_id=uuid4(), correlation_id=uuid4(), actor=ActorBitacora(
                tipo="USUARIO", usuario_id=actor_id, username_snapshot=prefix + "_actor",
                nombre_snapshot="Actor Audit", rol_snapshot=role_name,
            ), metodo_http="PUT", ruta_http="/usuarios/{user_id}",
            ip_hash="a" * 64, ip_hash_version=1, user_agent="Audit test",
        )

    ctx = context()

    def call(operation, session, *, update=None, audit_context=None):
        audit_context = audit_context or ctx
        if operation == "create":
            return routes.create_new_user(UserCreate(
                username=prefix + "_created", nombre="Created", apellido="Surname", id_rol=role_id,
                password="private-created-password", telefono="private-phone", fecha_nacimiento="1999-02-03",
            ), db=session, audit_context=audit_context)
        if operation == "update":
            return routes.update_existing_user(target_id, update or UserAdminUpdate(nombre="After", activo=False), db=session, audit_context=audit_context)
        if operation == "password":
            return routes.change_user_password(target_id, UserPasswordUpdate(new_password="new-secret-password"), db=session, audit_context=audit_context)
        return routes.delete_existing_user(target_id, db=session, audit_context=audit_context)

    yield SimpleNamespace(
        factory=factory, engine=engine, db_engine=persistent_test_engine, context=ctx, new_context=context,
        actor_id=actor_id, target_id=target_id, role_id=role_id, prefix=prefix, initial_hash=initial_hash,
        call=call, independent=independent,
    )
    # Only test-owned functional fixtures are removed; logical audit actor IDs survive.
    with persistent_test_engine.begin() as connection:
        ids = connection.execute(select(Usuario.id_usuario).where(Usuario.username.in_(
            [prefix + "_actor", prefix + "_target", prefix + "_created"],
        ))).scalars().all()
        if ids:
            connection.execute(Operador.__table__.delete().where(Operador.id_usuario.in_(ids)))
            connection.execute(Usuario.__table__.delete().where(Usuario.id_usuario.in_(ids)))
        connection.execute(Rol.__table__.delete().where(Rol.id_rol == role_id))


def user_row(case, *, created=False):
    with case.factory() as verification:
        username = case.prefix + ("_created" if created else "_target")
        return verification.execute(select(Usuario.__table__).where(Usuario.username == username)).mappings().one_or_none()


def audit_rows(case, context=None):
    with case.factory() as verification:
        return verification.execute(select(BitacoraEvento.__table__).where(
            BitacoraEvento.correlation_id == (context or case.context).correlation_id,
        )).mappings().all()


def assert_safe(rows, *extra_markers):
    for row in rows:
        payload = {key: row[key] for key in ("valores_anteriores", "valores_posteriores", "datos_evento", "error_mensaje")}
        encoded = json.dumps(payload, ensure_ascii=False)
        for forbidden in (
            "password", "password_hash", "token", "JWT", "Authorization", "telefono", "fecha_nacimiento",
            "private-phone", "1999-02-03", "private-created-password", "new-secret-password", *extra_markers,
        ):
            assert forbidden not in encoded


@pytest.mark.parametrize("operation,action", [
    ("create", "USUARIO_CREADO"), ("update", "USUARIO_ACTUALIZADO"),
    ("password", "USUARIO_CREDENCIAL_CAMBIADA"), ("delete", "USUARIO_ELIMINADO"),
])
def test_success_joint_commit_new_session_and_context(case, monkeypatch, operation, action):
    captured, commits = [], []
    real_create = crud_bitacora.create_bitacora_evento

    def audited(session, payload):
        captured.append((session, session.get_transaction()))
        assert not commits
        return real_create(session, payload)

    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", audited)
    with case.factory() as functional:
        event.listen(functional, "before_commit", lambda session: commits.append(True))
        result = case.call(operation, functional)
        assert captured[0][0] is functional
        assert len(commits) == 1 and not case.independent
    rows = audit_rows(case)
    assert len(rows) == 1 and rows[0]["accion"] == action and rows[0]["resultado"] == "EXITOSO"
    assert rows[0]["usuario_id"] == case.actor_id
    assert rows[0]["actor_username_snapshot"] == case.prefix + "_actor"
    assert rows[0]["request_id"] == case.context.request_id
    assert rows[0]["ip_hash"] == "a" * 64 and rows[0]["ruta_template"] == "/usuarios/{user_id}"
    assert_safe(rows, case.initial_hash)
    stored = user_row(case, created=operation == "create")
    if operation == "delete":
        assert stored is None and rows[0]["valores_anteriores"]["nombre"] == "Before"
    elif operation == "password":
        assert stored["password_hash"] != case.initial_hash
        assert verify_password("new-secret-password", stored["password_hash"])
        assert rows[0]["valores_anteriores"] is None and rows[0]["valores_posteriores"] is None
        assert rows[0]["datos_evento"] == {"credencial_cambiada": True}
        assert_safe(rows, stored["password_hash"])
    elif operation == "update":
        assert stored["nombre"] == "After" and not stored["activo"]
        assert rows[0]["valores_anteriores"] == {"nombre": "Before", "activo": True}
        assert rows[0]["valores_posteriores"] == {"nombre": "After", "activo": False}
        assert result.updated_at == stored["updated_at"]
    else:
        assert stored is not None and result.id_usuario == stored["id_usuario"]
        assert result.created_at == stored["created_at"] and result.updated_at == stored["updated_at"]


@pytest.mark.parametrize("operation", ["create", "update", "password", "delete"])
def test_audit_failure_rolls_back_business(case, monkeypatch, operation):
    real_create = crud_bitacora.create_bitacora_evento

    def missing_related_fk(session, payload):
        return real_create(session, payload.model_copy(update={"evento_relacionado_id": uuid4()}))

    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", missing_related_fk)
    before = user_row(case)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call(operation, functional)
        assert captured.value.status_code == 500
        assert captured.value.__cause__.__cause__.orig.sqlstate == "23503"
    assert user_row(case) == before and user_row(case, created=True) is None
    assert audit_rows(case) == [] and not case.independent
    assert verify_password("initial-password", user_row(case)["password_hash"])


@pytest.mark.parametrize("operation", ["create", "update", "password", "delete"])
def test_rollback_before_commit_observes_previous_state(case, monkeypatch, operation):
    before = user_row(case)
    with case.factory() as functional:
        commit = MockCommitRollback(functional)
        monkeypatch.setattr(functional, "commit", commit)
        with pytest.raises(HTTPException) as captured:
            case.call(operation, functional)
        assert captured.value.status_code == 500 and commit.calls == 1
    assert user_row(case) == before and user_row(case, created=True) is None and audit_rows(case) == []


class MockCommitRollback:
    def __init__(self, session):
        self.session, self.calls = session, 0

    def __call__(self):
        self.calls += 1
        self.session.rollback()
        raise RuntimeError("test caller rollback before commit")


@pytest.mark.parametrize("enabled", [True, False])
def test_noop_unchanged_timestamp_no_engine_or_update(case, monkeypatch, enabled):
    case.engine.enabled = enabled
    before = user_row(case)
    statements = []

    def sql(connection, cursor, statement, parameters, context, many):
        statements.append(statement.lstrip().upper())

    monkeypatch.setattr(case.engine, "operation", lambda *args, **kwargs: pytest.fail("No-op opened engine"))
    event.listen(case.db_engine, "before_cursor_execute", sql)
    try:
        with case.factory() as functional:
            event.listen(functional, "before_commit", lambda session: pytest.fail("No-op committed"))
            result = case.call("update", functional, update=UserAdminUpdate(nombre="Before", telefono="private-phone"))
            assert result.updated_at == before["updated_at"]
    finally:
        event.remove(case.db_engine, "before_cursor_execute", sql)
    assert not any(statement.startswith(("UPDATE", "INSERT", "DELETE")) for statement in statements)
    assert user_row(case) == before and audit_rows(case) == []


@pytest.mark.parametrize("mixed", [False, True])
def test_private_fields_changed_not_noop(case, mixed):
    fields = {"telefono": "new-private-phone", "fecha_nacimiento": "2001-02-03"}
    if mixed:
        fields["nombre"] = "After"
    with case.factory() as functional:
        case.call("update", functional, update=UserAdminUpdate(**fields))
    row = audit_rows(case)[0]
    assert row["valores_anteriores"] == ({"nombre": "Before"} if mixed else {})
    assert row["valores_posteriores"] == ({"nombre": "After"} if mixed else {})
    assert row["datos_evento"] == {"otros_datos_actualizados": True}
    assert user_row(case)["telefono"] == "new-private-phone"
    assert_safe([row], "new-private-phone", "2001-02-03")


@pytest.mark.parametrize("operation", ["create", "update", "password", "delete", "private_update"])
def test_disabled_cannot_bypass_requirement(case, operation):
    case.engine.enabled = False
    before = user_row(case)
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("update" if operation == "private_update" else operation, functional,
                      update=UserAdminUpdate(telefono="new-private-phone") if operation == "private_update" else None)
        assert captured.value.status_code == 503
    assert user_row(case) == before and user_row(case, created=True) is None and audit_rows(case) == []


@pytest.fixture
def blocking_fk(case):
    table = Table(
        "ua_fk_" + uuid4().hex, MetaData(),
        Column("user_id", Integer, ForeignKey(Usuario.__table__.c.id_usuario), primary_key=True), schema="public",
    )
    table.create(case.db_engine)
    try:
        with case.db_engine.begin() as connection:
            connection.execute(table.insert().values(user_id=case.target_id))
        yield table
    finally:
        table.drop(case.db_engine)


def test_known_delete_fk_surviving_failure_audit(case, blocking_fk):
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("delete", functional)
        assert captured.value.status_code == 409 and captured.value.__cause__.orig.sqlstate == "23503"
        assert captured.value.__cause__.orig.diag.table_name == blocking_fk.name
        assert len(case.independent) == 1 and case.independent[0] is not functional
    assert user_row(case) is not None
    rows = audit_rows(case)
    assert len(rows) == 1 and rows[0]["resultado"] == "FALLIDO"
    assert rows[0]["error_codigo"] == "USUARIO_ELIMINACION_BLOQUEADA" and rows[0]["error_mensaje"] is None
    assert_safe(rows, case.initial_hash)


def test_delete_not_null_no_failure_audit(case):
    with case.factory() as setup:
        setup.add(Operador(id_usuario=case.target_id, alias="Test", activo=True))
        setup.commit()
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("delete", functional)
        assert captured.value.status_code == 409
        assert captured.value.__cause__.orig.sqlstate == "23502"
        assert captured.value.__cause__.orig.diag.table_name == "operadores"
        assert captured.value.__cause__.orig.diag.column_name == "id_usuario"
    assert user_row(case) is not None and audit_rows(case) == [] and not case.independent
    with case.factory() as verification:
        assert verification.execute(select(Operador.id_usuario).where(Operador.id_usuario == case.target_id)).scalar_one() == case.target_id


def test_failure_audit_failure_visible(case, blocking_fk, monkeypatch):
    monkeypatch.setattr(crud_bitacora, "create_bitacora_evento", lambda *args: (_ for _ in ()).throw(AuditPayloadError()))
    with case.factory() as functional:
        with pytest.raises(HTTPException) as captured:
            case.call("delete", functional)
        assert captured.value.status_code == 500
        assert captured.value.__cause__.business_error.orig.sqlstate == "23503"
    assert user_row(case) is not None and audit_rows(case) == []


@pytest.mark.parametrize("mutation", ["UPDATE", "DELETE"])
def test_audit_remains_append_only(case, mutation):
    with case.factory() as functional:
        case.call("update", functional)
    row = audit_rows(case)[0]
    statement = (
        "UPDATE public.bitacora_eventos SET accion = 'CHANGE' WHERE id_evento = :id"
        if mutation == "UPDATE" else "DELETE FROM public.bitacora_eventos WHERE id_evento = :id"
    )
    with case.factory() as session:
        with pytest.raises(DBAPIError) as captured:
            session.execute(text(statement), {"id": row["id_evento"]})
        assert captured.value.orig.sqlstate == "55000"
        session.rollback()
    assert audit_rows(case)[0]["accion"] == "USUARIO_ACTUALIZADO"


@pytest.mark.parametrize("second", ["update", "delete", "noop", "stale_noop"])
def test_concurrent_snapshot_and_noop_after_wait(case, monkeypatch, second):
    # Synchronize at the real target query: first transaction owns the row lock.
    first_locked, second_started, release = Event(), Event(), Event()
    real_lookup = routes.get_user_by_id_for_update
    second_context = case.new_context()

    def lookup(db, user_id):
        if db.info.get("second"):
            second_started.set()
        target = real_lookup(db, user_id)
        if not db.info.get("second"):
            first_locked.set()
            assert release.wait(10)
        return target

    monkeypatch.setattr(routes, "get_user_by_id_for_update", lookup)

    def first():
        with case.factory() as session:
            case.call("update", session, update=UserAdminUpdate(nombre="Intermediate"))

    def following():
        with case.factory() as session:
            session.info["second"] = True
            name = "Intermediate" if second == "noop" else "Before" if second == "stale_noop" else "Final"
            return case.call("delete" if second == "delete" else "update", session,
                             update=UserAdminUpdate(nombre=name),
                             audit_context=second_context)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first)
        assert first_locked.wait(10)
        second_future = pool.submit(following)
        try:
            assert second_started.wait(10)
            assert not second_future.done()
        finally:
            release.set()
        first_future.result(timeout=20)
        second_future.result(timeout=20)
    rows = audit_rows(case, second_context)
    if second == "noop":
        assert rows == [] and user_row(case)["nombre"] == "Intermediate"
    elif second == "delete":
        assert user_row(case) is None and rows[0]["valores_anteriores"]["nombre"] == "Intermediate"
    else:
        name = "Before" if second == "stale_noop" else "Final"
        assert user_row(case)["nombre"] == name
        assert rows[0]["valores_anteriores"] == {"nombre": "Intermediate"}
        assert rows[0]["valores_posteriores"] == {"nombre": name}


def test_actor_can_be_deleted_without_audit_fk(case):
    with case.factory() as functional:
        routes.delete_existing_user(case.actor_id, db=functional, audit_context=case.context)
    with case.factory() as verification:
        assert verification.execute(select(Usuario.id_usuario).where(
            Usuario.id_usuario == case.actor_id,
        )).scalar_one_or_none() is None
        assert verification.execute(text(
            "SELECT count(*) FROM pg_catalog.pg_constraint c "
            "JOIN pg_catalog.pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey) "
            "WHERE c.contype = 'f' AND c.conrelid = 'public.bitacora_eventos'::regclass "
            "AND a.attname = 'usuario_id'"
        )).scalar_one() == 0
    rows = audit_rows(case)
    assert len(rows) == 1 and rows[0]["entidad_id"] == str(case.actor_id)
    assert rows[0]["usuario_id"] == case.actor_id and rows[0]["accion"] == "USUARIO_ELIMINADO"
    assert rows[0]["valores_anteriores"]["username"] == case.prefix + "_actor"
    assert_safe(rows, case.initial_hash)
