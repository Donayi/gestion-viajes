from datetime import UTC, datetime, timedelta
from contextlib import contextmanager
from inspect import signature
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.crud.crud_bitacora import (
    create_bitacora_evento,
    get_bitacora_evento_by_id,
    list_bitacora_eventos,
)
from app.models.models import BitacoraEvento
from app.schemas.bitacora import (
    ActorBitacora,
    BitacoraEventoCreateInternal,
    DatosAuditoriaBitacora,
    ReferenciaRegistroBitacora,
)


EXPECTED_COLUMNS = {
    "id_evento",
    "evento_relacionado_id",
    "categoria",
    "actor_tipo",
    "usuario_id",
    "actor_username_snapshot",
    "actor_username_normalizado",
    "actor_nombre_snapshot",
    "actor_rol_snapshot",
    "ocurrido_at",
    "retener_hasta",
    "modulo",
    "accion",
    "resultado",
    "entidad_tipo",
    "entidad_id",
    "request_id",
    "correlation_id",
    "metodo_http",
    "ruta_template",
    "ip_hash",
    "ip_hash_version",
    "user_agent",
    "valores_anteriores",
    "valores_posteriores",
    "datos_evento",
    "error_codigo",
    "error_mensaje",
    "schema_version",
}
EXPECTED_FUNCTIONAL_INDEXES = {
    "ix_bitacora_eventos_ocurrido_id",
    "ix_bitacora_eventos_categoria_ocurrido",
    "ix_bitacora_eventos_modulo_accion_ocurrido",
    "ix_bitacora_eventos_resultado_ocurrido",
    "ix_bitacora_eventos_usuario_ocurrido",
    "ix_bitacora_eventos_username_ocurrido",
    "ix_bitacora_eventos_entidad_ocurrido",
    "ix_bitacora_eventos_request_id",
}


@pytest.fixture(scope="module", autouse=True)
def install_bitacora_objects(persistent_test_engine):
    from app.bootstrap import schema_bootstrap

    original_engine = schema_bootstrap.engine
    with persistent_test_engine.connect() as connection:
        version = int(connection.exec_driver_sql("SHOW server_version_num").scalar_one())
        assert 160000 <= version < 170000
    schema_bootstrap.engine = persistent_test_engine
    try:
        schema_bootstrap.run_schema_bootstrap()
        yield
    finally:
        schema_bootstrap.engine = original_engine


def _evento(**overrides) -> BitacoraEvento:
    values = {
        "categoria": "FUNCIONAL",
        "actor_tipo": "SISTEMA",
        "modulo": "PRUEBA_BITACORA",
        "accion": "CREAR",
        "resultado": "EXITOSO",
        "correlation_id": uuid4(),
        "schema_version": 1,
    }
    values.update(overrides)
    return BitacoraEvento(**values)


def _evento_in(**overrides) -> BitacoraEventoCreateInternal:
    values = {
        "categoria": "FUNCIONAL",
        "actor": ActorBitacora(tipo="SISTEMA"),
        "modulo": "PRUEBA_BITACORA",
        "accion": "CREAR",
        "resultado": "EXITOSO",
        "correlation_id": uuid4(),
        "schema_version": 1,
    }
    values.update(overrides)
    return BitacoraEventoCreateInternal(**values)


def _assert_flush_rejected(db_session, constraint, sqlstate="23514", **overrides):
    db_session.add(_evento(**overrides))
    with pytest.raises(IntegrityError) as captured:
        db_session.flush()
    db_session.rollback()
    assert captured.value.orig.sqlstate == sqlstate
    assert captured.value.orig.diag.constraint_name == constraint


def _stored_event(session, event_id):
    return session.execute(
        BitacoraEvento.__table__.select().where(BitacoraEvento.id_evento == event_id)
    ).mappings().one()


@contextmanager
def _isolated_catalog_connection(engine):
    # DDL and test data are reverted even when an assertion fails.
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def test_model_catalog_columns_types_defaults_and_primary_key(persistent_test_engine):
    inspector = inspect(persistent_test_engine)
    assert "bitacora_eventos" in inspector.get_table_names(schema="public")
    assert BitacoraEvento.__table__.schema == "public"
    columns = {
        column["name"]: column
        for column in inspector.get_columns("bitacora_eventos", schema="public")
    }
    assert set(columns) == EXPECTED_COLUMNS
    assert str(columns["id_evento"]["type"]) == "UUID"
    assert str(columns["valores_anteriores"]["type"]) == "JSONB"
    assert "TIMESTAMP" in str(columns["ocurrido_at"]["type"])
    assert columns["ocurrido_at"]["type"].timezone is True
    assert columns["retener_hasta"]["type"].timezone is True
    assert "transaction_timestamp()" in columns["ocurrido_at"]["default"]
    assert "transaction_timestamp()" in columns["retener_hasta"]["default"]
    assert (
        "24" in columns["retener_hasta"]["default"]
        or "2 years" in columns["retener_hasta"]["default"]
    )
    assert columns["schema_version"]["default"] is None
    assert inspector.get_pk_constraint("bitacora_eventos", schema="public")["constrained_columns"] == ["id_evento"]
    for name in ("valores_anteriores", "valores_posteriores", "datos_evento"):
        assert str(columns[name]["type"]) == "JSONB"
    assert str(columns["modulo"]["type"]) == "VARCHAR(100)"
    assert str(columns["entidad_tipo"]["type"]) == "VARCHAR(100)"
    assert str(columns["ip_hash"]["type"]) == "CHAR(64)"
    for name in ("schema_version", "ip_hash_version"):
        assert str(columns[name]["type"]) == "SMALLINT"
        assert columns[name]["default"] is None
    required = {
        "id_evento", "categoria", "actor_tipo", "ocurrido_at", "retener_hasta",
        "modulo", "accion", "resultado", "schema_version",
    }
    assert {name for name, column in columns.items() if not column["nullable"]} == required
    expected_checks = {
        "categoria", "actor_tipo", "resultado", "schema_version", "trazabilidad",
        "no_autorreferencia", "ip_par", "ip_hash", "ip_hash_version", "usuario_snapshots",
        "usuario_id_actor", "error_codigo", "retencion", "entidad", "http_request",
    }
    assert {
        check["name"] for check in inspector.get_check_constraints("bitacora_eventos", schema="public")
    } == {f"ck_bitacora_eventos_{suffix}" for suffix in expected_checks}


def test_only_self_foreign_key_exists_and_user_id_has_no_fk(persistent_test_engine):
    foreign_keys = inspect(persistent_test_engine).get_foreign_keys("bitacora_eventos", schema="public")
    assert len(foreign_keys) == 1
    foreign_key = foreign_keys[0]
    assert foreign_key["constrained_columns"] == ["evento_relacionado_id"]
    assert foreign_key["referred_schema"] in (None, "public")
    assert foreign_key["referred_table"] == "bitacora_eventos"
    assert foreign_key["referred_columns"] == ["id_evento"]
    assert foreign_key["options"].get("ondelete") == "RESTRICT"
    with persistent_test_engine.connect() as connection:
        row = connection.execute(text(
            "SELECT confrelid='public.bitacora_eventos'::regclass, "
            "confdeltype, condeferrable, condeferred FROM pg_catalog.pg_constraint "
            "WHERE conrelid='public.bitacora_eventos'::regclass AND contype='f'"
        )).one()
    assert row == (True, "r", False, False)


@pytest.mark.parametrize("categoria", ["FUNCIONAL", "SEGURIDAD"])
def test_valid_categories_are_accepted(db_session, categoria):
    db_session.add(_evento(categoria=categoria))
    db_session.flush()


def test_invalid_category_is_rejected_by_postgresql(db_session):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_categoria", categoria="TECNICA")


@pytest.mark.parametrize("actor_tipo", ["USUARIO", "ANONIMO", "SISTEMA"])
def test_valid_actor_types_are_accepted(db_session, actor_tipo):
    snapshots = {}
    if actor_tipo == "USUARIO":
        snapshots = {
            "actor_username_snapshot": "admin",
            "actor_nombre_snapshot": "Usuario Histórico",
            "actor_rol_snapshot": "ADMIN",
        }
    db_session.add(_evento(actor_tipo=actor_tipo, **snapshots))
    db_session.flush()


def test_invalid_actor_type_is_rejected_by_postgresql(db_session):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_actor_tipo", actor_tipo="ROBOT")


@pytest.mark.parametrize("resultado", ["EXITOSO", "FALLIDO", "RECHAZADO"])
def test_valid_results_are_accepted(db_session, resultado):
    values = {"resultado": resultado}
    if resultado != "EXITOSO":
        values["error_codigo"] = "PRUEBA_CONTROLADA"
    db_session.add(_evento(**values))
    db_session.flush()


def test_invalid_result_and_schema_version_are_rejected(db_session):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_resultado", resultado="DESCONOCIDO")
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_schema_version", schema_version=0)


def test_request_or_correlation_is_required(db_session):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_trazabilidad", request_id=None, correlation_id=None)
    db_session.add(_evento(request_id=uuid4(), correlation_id=None))
    db_session.flush()


@pytest.mark.parametrize(
    "overrides",
    [
        {"ip_hash": "a" * 64, "ip_hash_version": None},
        {"ip_hash": None, "ip_hash_version": 1},
        {"ip_hash": "a" * 63, "ip_hash_version": 1},
        {"ip_hash": "A" * 64, "ip_hash_version": 1},
        {"ip_hash": "g" * 64, "ip_hash_version": 1},
        {"ip_hash": ("a" * 63) + " ", "ip_hash_version": 1},
    ],
)
def test_ip_constraints_reject_invalid_pairs_and_hashes(db_session, overrides):
    suffix = "ip_par" if (overrides["ip_hash"] is None or overrides["ip_hash_version"] is None) else "ip_hash"
    _assert_flush_rejected(db_session, f"ck_bitacora_eventos_{suffix}", **overrides)


def test_valid_lowercase_ip_hash_is_accepted(db_session):
    db_session.add(_evento(ip_hash="0123456789abcdef" * 4, ip_hash_version=1))
    db_session.flush()


@pytest.mark.parametrize(
    "missing",
    ["actor_username_snapshot", "actor_nombre_snapshot", "actor_rol_snapshot"],
)
@pytest.mark.parametrize("invalid", [None, "   "])
def test_user_requires_all_non_blank_snapshots(db_session, missing, invalid):
    values = {
        "actor_tipo": "USUARIO",
        "actor_username_snapshot": "admin",
        "actor_nombre_snapshot": "Nombre",
        "actor_rol_snapshot": "ADMIN",
    }
    values[missing] = invalid
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_usuario_snapshots", **values)


@pytest.mark.parametrize("actor_tipo", ["ANONIMO", "SISTEMA"])
def test_non_user_actor_rejects_user_id(db_session, actor_tipo):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_usuario_id_actor", actor_tipo=actor_tipo, usuario_id=99)


def test_anonymous_actor_can_keep_login_username(db_session):
    db_session.add(
        _evento(
            categoria="SEGURIDAD",
            actor_tipo="ANONIMO",
            actor_username_snapshot="usuario.intentado",
            actor_username_normalizado="usuario.intentado",
            resultado="RECHAZADO",
            error_codigo="LOGIN_INVALIDO",
        )
    )
    db_session.flush()


@pytest.mark.parametrize("resultado", ["FALLIDO", "RECHAZADO"])
def test_failed_or_rejected_result_requires_error_code(db_session, resultado):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_error_codigo", resultado=resultado, error_codigo="   ")


def test_entity_fields_must_coexist_and_be_non_blank(db_session):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_entidad", entidad_tipo="VIAJE", entidad_id=None)
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_entidad", entidad_tipo=None, entidad_id="1")
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_entidad", entidad_tipo="VIAJE", entidad_id="   ")
    db_session.add(_evento(entidad_tipo="VIAJE", entidad_id="1"))
    db_session.flush()


def test_retention_and_direct_self_reference_are_rejected(db_session):
    now = datetime.now(UTC)
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_retencion", ocurrido_at=now, retener_hasta=now)
    event_id = uuid4()
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_no_autorreferencia", id_evento=event_id, evento_relacionado_id=event_id)


def test_http_fields_require_request_id_but_request_id_needs_no_http_fields(db_session):
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_http_request", metodo_http="POST", request_id=None)
    _assert_flush_rejected(db_session, "ck_bitacora_eventos_http_request", ruta_template="RUTA_NO_RESUELTA", request_id=None)
    db_session.add(_evento(request_id=uuid4(), correlation_id=None))
    db_session.flush()


def test_calendar_retention_defaults_and_transaction_timestamp(db_session):
    instant = db_session.execute(text("SELECT transaction_timestamp()")).scalar_one()
    first = _evento()
    second = _evento()
    db_session.add(first)
    db_session.flush()
    db_session.add(second)
    db_session.flush()
    expected = db_session.execute(
        text("SELECT transaction_timestamp() + INTERVAL '24 months'"),
    ).scalar_one()
    for event in (first, second):
        stored = _stored_event(db_session, event.id_evento)
        assert stored["ocurrido_at"] == instant
        assert stored["retener_hasta"] == expected


def test_expired_retention_is_informational_and_bootstrap_does_not_delete(
    db_session,
    monkeypatch,
):
    from app.bootstrap import schema_bootstrap

    occurred = datetime.now(UTC) - timedelta(days=1000)
    event = _evento(
        ocurrido_at=occurred,
        retener_hasta=occurred + timedelta(days=800),
    )
    db_session.add(event)
    db_session.flush()
    original = dict(_stored_event(db_session, event.id_evento))
    # Bind every bootstrap transaction to the SAME real PostgreSQL connection,
    # so bootstrap can see this row without leaking a physical commit into other tests.
    connection = db_session.connection()

    class TransactionalBootstrapBind:
        @contextmanager
        def begin(self):
            with connection.begin_nested():
                yield connection

        def _run_ddl_visitor(self, visitor, element, **kwargs):
            return connection._run_ddl_visitor(visitor, element, **kwargs)

    monkeypatch.setattr(schema_bootstrap, "engine", TransactionalBootstrapBind())
    schema_bootstrap.run_schema_bootstrap()
    # SQL reads the row independently of the ORM identity map.
    assert dict(_stored_event(db_session, event.id_evento)) == original
    assert original["retener_hasta"] < datetime.now(UTC)


def test_jsonb_does_not_replace_application_limits(db_session):
    # Does not exceed key count/string limits: application rejection concerns bytes.
    oversized = {f"key_{index}": "x" * 500 for index in range(20)}
    event = _evento(datos_evento=oversized)
    db_session.add(event)
    db_session.flush()
    assert _stored_event(db_session, event.id_evento)["datos_evento"] == oversized
    with pytest.raises(ValidationError) as captured:
        DatosAuditoriaBitacora(datos_evento=oversized)
    assert "bytes UTF-8" in captured.value.errors()[0]["msg"]


def test_crud_flushes_without_commit_and_rollback_removes(db_session):
    created = create_bitacora_evento(db_session, _evento_in())
    assert created.id_evento is not None
    assert get_bitacora_evento_by_id(db_session, created.id_evento) is created
    event_id = created.id_evento
    db_session.rollback()
    assert get_bitacora_evento_by_id(db_session, event_id) is None


def test_caller_commit_persists_with_independent_session(persistent_test_engine):
    unique_module = f"COMMIT_{uuid4().hex.upper()}"
    # Caller commit releases a savepoint; outer rollback prevents fixture leakage.
    # This checks Session.commit ownership, not durability across physical connections.
    with _isolated_catalog_connection(persistent_test_engine) as connection:
        with Session(connection, join_transaction_mode="create_savepoint") as session:
            created = create_bitacora_evento(session, _evento_in(modulo=unique_module))
            event_id = created.id_evento
            session.commit()
        with Session(connection, join_transaction_mode="create_savepoint") as verification:
            loaded = get_bitacora_evento_by_id(verification, event_id)
            assert loaded is not None
            assert loaded.modulo == unique_module


def test_get_missing_and_empty_filtered_list(db_session):
    created = create_bitacora_evento(db_session, _evento_in())
    event_id = created.id_evento
    db_session.expunge_all()
    assert get_bitacora_evento_by_id(db_session, event_id).id_evento == event_id
    assert get_bitacora_evento_by_id(db_session, uuid4()) is None
    items, total = list_bitacora_eventos(db_session, modulo=f"VACIO_{uuid4().hex}")
    assert items == []
    assert total == 0


def test_list_order_filters_combination_and_pagination(db_session):
    base = datetime(2026, 8, 13, 12, tzinfo=UTC)
    module = f"LISTA_{uuid4().hex.upper()}"
    request_id = uuid4()
    inputs = [
        _evento_in(
            modulo=module,
            accion="ACTUALIZAR",
            ocurrido_at=base,
            retener_hasta=base + timedelta(days=800),
            request_id=request_id,
            correlation_id=None,
            actor=ActorBitacora(
                tipo="USUARIO",
                usuario_id=7,
                username_snapshot="Admin",
                nombre_snapshot="Administrador",
                rol_snapshot="ADMIN",
            ),
            actor_username_normalizado="Admin",
            entidad=ReferenciaRegistroBitacora(entidad_tipo="VIAJE", entidad_id="42"),
        ),
        _evento_in(
            modulo=module,
            ocurrido_at=base + timedelta(seconds=1),
            retener_hasta=base + timedelta(days=800),
        ),
    ]
    created = [create_bitacora_evento(db_session, item) for item in inputs]
    items, total = list_bitacora_eventos(db_session, modulo=module, page_size=1)
    assert total == 2
    assert items == [created[1]]
    second_page, _ = list_bitacora_eventos(db_session, modulo=module, page=2, page_size=1)
    assert second_page == [created[0]]
    filtered, filtered_total = list_bitacora_eventos(
        db_session,
        fecha_inicial=base,
        fecha_final=base,
        categoria="FUNCIONAL",
        modulo=module,
        accion="ACTUALIZAR",
        resultado="EXITOSO",
        usuario_id=7,
        actor_username_normalizado="Admin",
        entidad_tipo="VIAJE",
        entidad_id="42",
        request_id=request_id,
    )
    assert filtered == [created[0]]
    assert filtered_total == 1


def test_list_uuid_tiebreaker_and_limits(db_session):
    occurred = datetime(2026, 8, 13, 15, tzinfo=UTC)
    module = f"TIE_{uuid4().hex.upper()}"
    low = UUID("00000000-0000-0000-0000-000000000001")
    high = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    db_session.add_all(
        [
            _evento(id_evento=low, modulo=module, ocurrido_at=occurred, retener_hasta=occurred + timedelta(days=800)),
            _evento(id_evento=high, modulo=module, ocurrido_at=occurred, retener_hasta=occurred + timedelta(days=800)),
        ]
    )
    db_session.flush()
    items, _ = list_bitacora_eventos(db_session, modulo=module)
    assert [item.id_evento for item in items] == [high, low]
    with pytest.raises(ValueError):
        list_bitacora_eventos(db_session, page=0)
    with pytest.raises(ValueError):
        list_bitacora_eventos(db_session, page_size=0)
    with pytest.raises(ValueError):
        list_bitacora_eventos(db_session, page_size=101)


@pytest.mark.parametrize("operation", ["sql_update", "sql_delete", "orm_update", "orm_delete"])
def test_immutable_event_and_same_session_recovery(db_session, operation):
    event = _evento(datos_evento={"prueba": "original"})
    db_session.add(event)
    db_session.flush()
    event_id = event.id_evento
    original = dict(_stored_event(db_session, event_id))
    # Roll back only the mutation savepoint, preserving the fixture's original INSERT.
    savepoint = db_session.begin_nested()
    with pytest.raises(DBAPIError) as captured:
        if operation == "sql_update":
            db_session.execute(text(
                "UPDATE public.bitacora_eventos SET accion='CAMBIAR' WHERE id_evento=:id"
            ), {"id": event_id})
        elif operation == "sql_delete":
            db_session.execute(text(
                "DELETE FROM public.bitacora_eventos WHERE id_evento=:id"
            ), {"id": event_id})
        elif operation == "orm_update":
            event.accion = "CAMBIAR"
            db_session.flush()
        else:
            db_session.delete(event)
            db_session.flush()
    savepoint.rollback()
    assert captured.value.orig.sqlstate == "55000"
    db_session.expire_all()
    assert dict(_stored_event(db_session, event_id)) == original
    subsequent = create_bitacora_evento(db_session, _evento_in())
    assert _stored_event(db_session, subsequent.id_evento)["id_evento"] == subsequent.id_evento


def test_function_trigger_and_bootstrap_are_exact_and_idempotent(persistent_test_engine):
    from app.bootstrap import schema_bootstrap

    original_engine = schema_bootstrap.engine
    schema_bootstrap.engine = persistent_test_engine
    try:
        schema_bootstrap.run_schema_bootstrap()
        schema_bootstrap.run_schema_bootstrap()
    finally:
        schema_bootstrap.engine = original_engine
    with persistent_test_engine.connect() as connection:
        function = connection.execute(
            text(
                "SELECT l.lanname, p.prosecdef, p.proconfig, p.prosrc, "
                "pg_get_function_result(p.oid) "
                "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                "JOIN pg_language l ON l.oid=p.prolang "
                "WHERE n.nspname='public' AND p.proname='prevent_bitacora_mutation' "
                "AND pg_get_function_identity_arguments(p.oid)=''"
            )
        ).one()
        assert function[0] == "plpgsql"
        assert function[1] is False
        assert function[2] == ["search_path=pg_catalog"]
        assert function[3].strip(" \t\r\n") == schema_bootstrap._BITACORA_FUNCTION_BODY
        assert function[4] == "trigger"
        trigger = connection.execute(
            text(
                "SELECT n.nspname, c.relname, t.tgtype, t.tgenabled, "
                "p.proname, t.tgqual, t.tgfoid = 'public.prevent_bitacora_mutation()'::regprocedure "
                "FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
                "JOIN pg_namespace n ON n.oid=c.relnamespace "
                "JOIN pg_proc p ON p.oid=t.tgfoid "
                "WHERE t.tgname='trg_bitacora_eventos_immutable' AND NOT t.tgisinternal"
            )
        ).one()
        assert trigger == ("public", "bitacora_eventos", 26, "O", "prevent_bitacora_mutation", None, True)


@pytest.mark.parametrize("variant", ["update_only", "condition", "wrong_table"])
def test_bootstrap_rejects_incompatible_trigger_without_replacing(persistent_test_engine, variant):
    from app.bootstrap.schema_bootstrap import _install_bitacora_immutability
    from app.services.backup_service import _load_inventory

    with _isolated_catalog_connection(persistent_test_engine) as connection:
        connection.exec_driver_sql("DROP TRIGGER trg_bitacora_eventos_immutable ON public.bitacora_eventos")
        table = "roles" if variant == "wrong_table" else "bitacora_eventos"
        events = "UPDATE" if variant == "update_only" else "UPDATE OR DELETE"
        condition = "WHEN (false) " if variant == "condition" else ""
        connection.exec_driver_sql(
            f"CREATE TRIGGER trg_bitacora_eventos_immutable BEFORE {events} "
            f"ON public.{table} FOR EACH STATEMENT {condition}"
            "EXECUTE FUNCTION public.prevent_bitacora_mutation()"
        )
        oid = connection.execute(text(
            "SELECT oid FROM pg_catalog.pg_trigger "
            "WHERE tgname='trg_bitacora_eventos_immutable' AND NOT tgisinternal"
        )).scalar_one()
        with pytest.raises(RuntimeError, match="trigger.*incompatible"):
            _install_bitacora_immutability(connection)
        assert connection.execute(text(
            "SELECT oid FROM pg_catalog.pg_trigger "
            "WHERE tgname='trg_bitacora_eventos_immutable' AND NOT tgisinternal"
        )).scalar_one() == oid
        assert _load_inventory(connection).triggers == frozenset()


@pytest.mark.parametrize("variant", ["different_body", "different_state", "internal_space", "comment"])
def test_bootstrap_and_inventory_reject_noncanonical_body(persistent_test_engine, variant):
    from app.bootstrap.schema_bootstrap import _BITACORA_FUNCTION_BODY, _install_bitacora_immutability
    from app.services.backup_service import _load_inventory

    bodies = {
        "different_body": "BEGIN RETURN NULL; END;",
        "different_state": _BITACORA_FUNCTION_BODY.replace("55000", "55001"),
        "internal_space": _BITACORA_FUNCTION_BODY.replace("RAISE EXCEPTION", "RAISE  EXCEPTION"),
        "comment": _BITACORA_FUNCTION_BODY.replace("BEGIN", "BEGIN -- comentario"),
    }
    with _isolated_catalog_connection(persistent_test_engine) as connection:
        connection.exec_driver_sql("DROP TRIGGER trg_bitacora_eventos_immutable ON public.bitacora_eventos")
        connection.exec_driver_sql("DROP FUNCTION public.prevent_bitacora_mutation()")
        connection.exec_driver_sql(
            "CREATE FUNCTION public.prevent_bitacora_mutation() RETURNS trigger "
            "LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog "
            f"AS $audit${bodies[variant]}$audit$"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER trg_bitacora_eventos_immutable BEFORE UPDATE OR DELETE "
            "ON public.bitacora_eventos FOR EACH STATEMENT "
            "EXECUTE FUNCTION public.prevent_bitacora_mutation()"
        )
        with pytest.raises(RuntimeError, match="función.*incompatible"):
            _install_bitacora_immutability(connection)
        assert _load_inventory(connection).functions == frozenset()
        assert _load_inventory(connection).triggers == frozenset()


def test_exact_authorized_indexes_and_directions(persistent_test_engine):
    with persistent_test_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE schemaname='public' AND tablename='bitacora_eventos'"
            )
        ).all()
    definitions = {name: definition for name, definition in rows}
    assert set(definitions) == EXPECTED_FUNCTIONAL_INDEXES | {"bitacora_eventos_pkey"}
    assert "ocurrido_at DESC, id_evento DESC" in definitions["ix_bitacora_eventos_ocurrido_id"]
    assert "categoria, ocurrido_at DESC" in definitions["ix_bitacora_eventos_categoria_ocurrido"]
    assert "modulo, accion, ocurrido_at DESC" in definitions["ix_bitacora_eventos_modulo_accion_ocurrido"]
    assert "resultado, ocurrido_at DESC" in definitions["ix_bitacora_eventos_resultado_ocurrido"]
    assert "usuario_id, ocurrido_at DESC" in definitions["ix_bitacora_eventos_usuario_ocurrido"]
    assert "actor_username_normalizado, ocurrido_at DESC" in definitions["ix_bitacora_eventos_username_ocurrido"]
    assert "entidad_tipo, entidad_id, ocurrido_at DESC" in definitions["ix_bitacora_eventos_entidad_ocurrido"]
    assert definitions["ix_bitacora_eventos_request_id"].endswith("(request_id)")
    all_definitions = "\n".join(definitions.values()).lower()
    assert " using gin " not in all_definitions
    assert "retener_hasta" not in all_definitions
    assert "correlation_id" not in all_definitions


def test_crud_is_append_only_and_has_no_generic_orm_serialization():
    import ast

    source = (
        Path(__file__).resolve().parents[1] / "app/crud/crud_bitacora.py"
    ).read_text(encoding="utf-8")
    assert "db.commit(" not in source
    assert "db.delete(" not in source
    assert "def update_" not in source
    assert "def delete_" not in source
    assert "model_dump(" not in source
    assert "**values" not in source
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    attributes = {node.func.attr for node in calls if isinstance(node.func, ast.Attribute)}
    assert not attributes & {"commit", "rollback", "update", "delete", "execute", "exec_driver_sql", "model_dump"}
    assert {"add", "flush"} <= attributes
    assert all(keyword.arg is not None for node in calls for keyword in node.keywords)
    assert "correlation_id" not in signature(list_bitacora_eventos).parameters
    assert "FastAPI" not in source
    assert "Request" not in source
    assert {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    } == {"create_bitacora_evento", "get_bitacora_evento_by_id", "list_bitacora_eventos"}


def test_related_event_valid_without_chronological_precedence(db_session):
    later = _evento(ocurrido_at=datetime(2026, 8, 2, tzinfo=UTC))
    db_session.add(later)
    db_session.flush()
    earlier = create_bitacora_evento(db_session, _evento_in(
        evento_relacionado_id=later.id_evento,
        ocurrido_at=datetime(2026, 8, 1, tzinfo=UTC),
        retener_hasta=datetime(2028, 8, 1, tzinfo=UTC),
    ))
    assert _stored_event(db_session, earlier.id_evento)["evento_relacionado_id"] == later.id_evento


def test_nonexistent_related_event_rejected_by_fk(db_session):
    constraint = db_session.execute(text(
        "SELECT conname FROM pg_catalog.pg_constraint "
        "WHERE conrelid='public.bitacora_eventos'::regclass AND contype='f'"
    )).scalar_one()
    _assert_flush_rejected(
        db_session, constraint, sqlstate="23503", evento_relacionado_id=uuid4()
    )


@pytest.mark.parametrize("version", [1, 32767])
def test_smallint_versions_valid_boundaries(db_session, version):
    event = create_bitacora_evento(db_session, _evento_in(
        schema_version=version, ip_hash="0123456789abcdef" * 4, ip_hash_version=version
    ))
    stored = _stored_event(db_session, event.id_evento)
    assert stored["schema_version"] == stored["ip_hash_version"] == version


@pytest.mark.parametrize("field", ["schema_version", "ip_hash_version"])
@pytest.mark.parametrize("version", [0, -1, 32768])
def test_pydantic_smallint_range(field, version):
    values = {field: version}
    if field == "ip_hash_version":
        values["ip_hash"] = "a" * 64
    with pytest.raises(ValidationError) as captured:
        _evento_in(**values)
    assert any(error["loc"] == (field,) for error in captured.value.errors())


@pytest.mark.parametrize("field", ["schema_version", "ip_hash_version"])
def test_postgresql_smallint_overflow(db_session, field):
    values = {field: 32768}
    if field == "ip_hash_version":
        values["ip_hash"] = "a" * 64
    db_session.add(_evento(**values))
    with pytest.raises(DBAPIError) as captured:
        db_session.flush()
    db_session.rollback()
    assert captured.value.orig.sqlstate == "22003"


@pytest.mark.parametrize("version", [0, -1])
def test_postgresql_ip_version_positive_check(db_session, version):
    _assert_flush_rejected(
        db_session, "ck_bitacora_eventos_ip_hash_version",
        ip_hash="a" * 64, ip_hash_version=version,
    )


@pytest.mark.parametrize("values", [{"ip_hash": "a" * 64}, {"ip_hash_version": 1}])
def test_pydantic_ip_pair(values):
    with pytest.raises(ValidationError):
        _evento_in(**values)


def test_ip_hash_stored_value_not_pre_cast_input(db_session):
    valid = "0123456789abcdef" * 4
    # bpchar conversion discards excess spaces before CHECK evaluation.
    event = _evento(ip_hash=valid + "   ", ip_hash_version=1)
    db_session.add(event)
    db_session.flush()
    assert _stored_event(db_session, event.id_evento)["ip_hash"] == valid
    lengths = db_session.execute(text(
        "SELECT octet_length(ip_hash), length(ip_hash::text) "
        "FROM public.bitacora_eventos WHERE id_evento=:id"
    ), {"id": event.id_evento}).one()
    assert lengths == (64, 64)
    cast_id = uuid4()
    db_session.execute(text(
        "INSERT INTO public.bitacora_eventos "
        "(id_evento,categoria,actor_tipo,modulo,accion,resultado,correlation_id,"
        "schema_version,ip_hash,ip_hash_version) VALUES "
        "(:id,'FUNCIONAL','SISTEMA','PRUEBA','CREAR','EXITOSO',:correlation,"
        "1,CAST(:input AS CHAR(64)),1)"
    ), {"id": cast_id, "correlation": uuid4(), "input": valid + "INVALIDO"})
    assert _stored_event(db_session, cast_id)["ip_hash"] == valid
    with pytest.raises(ValidationError):
        _evento_in(ip_hash=valid + "INVALIDO", ip_hash_version=1)


def test_list_real_page_sizes_and_order(db_session):
    module = f"PAGINA_{uuid4().hex.upper()}"
    occurred = datetime(2026, 8, 13, tzinfo=UTC)
    events = [
        _evento(modulo=module, ocurrido_at=occurred + timedelta(seconds=index // 2),
                retener_hasta=datetime(2028, 8, 13, tzinfo=UTC))
        for index in range(101)
    ]
    db_session.add_all(events)
    db_session.flush()
    expected = sorted(events, key=lambda event: (event.ocurrido_at, event.id_evento.int), reverse=True)
    first, total = list_bitacora_eventos(db_session, modulo=module)
    assert total == 101
    assert first == expected[:25]
    hundred, total = list_bitacora_eventos(db_session, modulo=module, page_size=100)
    assert total == 101
    assert hundred == expected[:100]
    last, _ = list_bitacora_eventos(db_session, modulo=module, page=2, page_size=100)
    assert last == expected[100:]


@pytest.mark.parametrize("field,match,other", [
    ("categoria", "FUNCIONAL", "SEGURIDAD"),
    ("modulo", "MODULO_UNO", "MODULO_DOS"),
    ("accion", "CREAR", "CONSULTAR"),
    ("resultado", "EXITOSO", "FALLIDO"),
    ("usuario_id", 71, 72),
    ("actor_username_normalizado", "usuario.uno", "usuario.dos"),
    ("entidad_tipo", "VIAJE", "CLIENTE"),
    ("entidad_id", "41", "42"),
    ("request_id", UUID(int=71), UUID(int=72)),
    ("fecha_inicial", datetime(2026, 8, 13, tzinfo=UTC), datetime(2026, 8, 12, tzinfo=UTC)),
    ("fecha_final", datetime(2026, 8, 13, tzinfo=UTC), datetime(2026, 8, 14, tzinfo=UTC)),
])
def test_each_filter_has_discriminating_data(db_session, field, match, other):
    request_id = uuid4()
    module = f"FILTRO_{uuid4().hex.upper()}"
    values = {
        "request_id": request_id, "modulo": module,
        "actor_tipo": "USUARIO", "usuario_id": 71,
        "actor_username_snapshot": "usuario.prueba", "actor_nombre_snapshot": "Usuario Prueba",
        "actor_rol_snapshot": "ADMIN", "actor_username_normalizado": "usuario.prueba",
        "entidad_tipo": "VIAJE", "entidad_id": "41", "error_codigo": "PRUEBA",
        "ocurrido_at": datetime(2026, 8, 13, tzinfo=UTC),
        "retener_hasta": datetime(2028, 8, 13, tzinfo=UTC),
    }
    column = "ocurrido_at" if field.startswith("fecha_") else field
    selected = _evento(**(values | {column: match}))
    excluded = _evento(**(values | {column: other}))
    db_session.add_all([selected, excluded])
    db_session.flush()
    # The scope filter matches BOTH rows, so cannot hide a missing tested filter.
    scope = {"modulo": module} if field == "request_id" else {"request_id": request_id}
    items, total = list_bitacora_eventos(db_session, **(scope | {field: match}))
    assert items == [selected]
    assert total == 1


def test_filters_combine_with_and(db_session):
    request_id = uuid4()
    events = [
        _evento(request_id=request_id, categoria=category, accion=action)
        for category, action in (
            ("FUNCIONAL", "CREAR"), ("FUNCIONAL", "CONSULTAR"), ("SEGURIDAD", "CREAR")
        )
    ]
    db_session.add_all(events)
    db_session.flush()
    assert list_bitacora_eventos(
        db_session, request_id=request_id, categoria="FUNCIONAL", accion="CREAR"
    ) == ([events[0]], 1)


@pytest.mark.parametrize("occurred,expected", [
    (datetime(2024, 2, 29, 12, tzinfo=UTC), datetime(2026, 2, 28, 12, tzinfo=UTC)),
    (datetime(2025, 1, 31, 12, tzinfo=UTC), datetime(2027, 1, 31, 12, tzinfo=UTC)),
    (datetime(2023, 3, 1, tzinfo=UTC), datetime(2025, 3, 1, tzinfo=UTC)),
])
def test_calendar_edge_dates_are_stored(db_session, occurred, expected):
    # Historical INSERTs exercise PostgreSQL calendar arithmetic, not a mocked default clock.
    db_session.execute(text("SET LOCAL TIME ZONE 'UTC'"))
    event_id = uuid4()
    db_session.execute(text(
        "INSERT INTO public.bitacora_eventos "
        "(id_evento,categoria,actor_tipo,modulo,accion,resultado,correlation_id,"
        "schema_version,ocurrido_at,retener_hasta) VALUES "
        "(:id,'FUNCIONAL','SISTEMA','PRUEBA','CREAR','EXITOSO',:correlation,1,"
        "CAST(:occurred AS TIMESTAMPTZ),CAST(:occurred AS TIMESTAMPTZ)+INTERVAL '24 months')"
    ), {"id": event_id, "correlation": uuid4(), "occurred": occurred})
    stored = _stored_event(db_session, event_id)
    assert stored["ocurrido_at"] == occurred
    assert stored["retener_hasta"] == expected
    if occurred.year == 2023:
        assert stored["retener_hasta"] != occurred + timedelta(days=730)


def test_bootstrap_inventory_same_peripheral_normalization(persistent_test_engine):
    from app.bootstrap.schema_bootstrap import _BITACORA_FUNCTION_BODY, _install_bitacora_immutability
    from app.services.backup_service import _load_inventory

    with _isolated_catalog_connection(persistent_test_engine) as connection:
        connection.exec_driver_sql("DROP TRIGGER trg_bitacora_eventos_immutable ON public.bitacora_eventos")
        connection.exec_driver_sql("DROP FUNCTION public.prevent_bitacora_mutation()")
        body = " \t\r\n" + _BITACORA_FUNCTION_BODY + "\n\r\t "
        connection.exec_driver_sql(
            "CREATE FUNCTION public.prevent_bitacora_mutation() RETURNS trigger "
            "LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog "
            f"AS $audit${body}$audit$"
        )
        _install_bitacora_immutability(connection)
        inventory = _load_inventory(connection)
        assert inventory.functions == frozenset({"prevent_bitacora_mutation()"})
        assert inventory.triggers == frozenset({("bitacora_eventos", "trg_bitacora_eventos_immutable")})


def test_real_bootstrap_inventory_and_dump_toc(persistent_test_engine, tmp_path):
    from app.bootstrap.schema_bootstrap import _BITACORA_FUNCTION_BODY
    from app.services import backup_service as service
    from app.services.restore_service import _validate_and_compare_toc

    # Requires pg_dump and pg_restore 16 on PATH in the test runner; never restores data.
    pg_dump, pg_restore = service.validate_postgresql_tools()
    args, environment = service._connection_parameters(
        persistent_test_engine.url.render_as_string(hide_password=False)
    )
    dump_path = tmp_path / "audit.dump"
    list_path = tmp_path / "audit.list"
    with persistent_test_engine.connect() as connection:
        try:
            snapshot = service.export_snapshot(connection)
            inventory = service._load_inventory(connection)
            assert inventory.functions == frozenset({"prevent_bitacora_mutation()"})
            assert inventory.triggers == frozenset({("bitacora_eventos", "trg_bitacora_eventos_immutable")})
            source = connection.execute(text(
                "SELECT prosrc FROM pg_catalog.pg_proc "
                "WHERE oid='public.prevent_bitacora_mutation()'::regprocedure"
            )).scalar_one()
            assert source.strip(" \t\r\n") == _BITACORA_FUNCTION_BODY
            service._run_pg_dump(
                pg_dump, connection_args=args, environment=environment,
                snapshot_id=snapshot, dump_path=dump_path,
            )
            service._generate_restore_list(
                pg_restore, dump_path=dump_path, restore_list_path=list_path, inventory=inventory,
            )
            toc = list_path.read_text(encoding="utf-8")
            approved = service.validate_restore_toc(toc, inventory)
            objects = [
                service._split_toc_entry(line)
                for line in approved if line and not line.lstrip().startswith(";")
            ]
            assert [fields[:2] for kind, fields in objects if kind == "FUNCTION"] == [
                ["public", "prevent_bitacora_mutation()"]
            ]
            assert [fields[:3] for kind, fields in objects if kind == "TRIGGER"] == [
                ["public", "bitacora_eventos", "trg_bitacora_eventos_immutable"]
            ]
            assert _validate_and_compare_toc(toc, toc, inventory=inventory)
        finally:
            connection.rollback()


def test_real_catalog_arbitrary_objects_not_authorized(persistent_test_engine):
    from app.services import backup_service as service
    from app.services.restore_service import RestorePreparationError, _validate_and_compare_toc

    with _isolated_catalog_connection(persistent_test_engine) as connection:
        connection.exec_driver_sql(
            "CREATE FUNCTION public.bitacora_prueba_arbitraria() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN RETURN NULL; END; $$"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER bitacora_prueba_arbitraria BEFORE UPDATE ON public.bitacora_eventos "
            "FOR EACH STATEMENT EXECUTE FUNCTION public.bitacora_prueba_arbitraria()"
        )
        inventory = service._load_inventory(connection)
        function = connection.execute(text(
            "SELECT p.oid,n.nspname,p.proname || '()' FROM pg_catalog.pg_proc p "
            "JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace "
            "WHERE n.nspname='public' AND p.proname='bitacora_prueba_arbitraria'"
        )).one()
        trigger = connection.execute(text(
            "SELECT t.oid,n.nspname,c.relname,t.tgname FROM pg_catalog.pg_trigger t "
            "JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid "
            "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "WHERE t.tgname='bitacora_prueba_arbitraria'"
        )).one()
        # Construct TOC records from actual catalog identities, without a mocked inventory.
        lines = [
            f"1; 1255 {function[0]} FUNCTION {function[1]} {function[2]} owner",
            f"2; 2620 {trigger[0]} TRIGGER {trigger[1]} {trigger[2]} {trigger[3]} owner",
        ]
        assert function[2] not in inventory.functions
        assert (trigger[2], trigger[3]) not in inventory.triggers
        for line in lines:
            with pytest.raises(service.BackupGenerationError) as captured:
                service.validate_restore_toc(line, inventory)
            assert captured.value.code == service.UNEXPECTED_TOC_OBJECT
            with pytest.raises(RestorePreparationError) as captured:
                _validate_and_compare_toc(line, line, inventory=inventory)
            assert captured.value.code == "TOC_VALIDATION_FAILED"
