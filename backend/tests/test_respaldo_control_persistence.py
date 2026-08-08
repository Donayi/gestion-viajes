from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.crud.crud_respaldos import get_estado_mantenimiento, set_estado_mantenimiento
from app.models.models import (
    ConfirmacionRestauracionControl,
    EstadoSistemaControl,
    OperacionRespaldoControl,
    RespaldoControl,
    TicketDescargaControl,
    ValidacionRespaldoControl,
    WorkerRespaldoControl,
)


CONTROL_SCHEMA = "control_respaldo"
EXPECTED_TABLES = {
    "respaldos",
    "operaciones_respaldo",
    "validaciones_respaldo",
    "confirmaciones_restauracion",
    "estado_sistema",
    "workers_respaldo",
    "tickets_descarga",
}


def _respaldo(**overrides):
    unique = uuid4().hex
    values = {
        "nombre_archivo": f"dafreq-{unique}.dafreq-backup",
        "ruta_relativa": f"packages/{unique}.dafreq-backup",
        "origen": "MANUAL",
        "estado": "PENDIENTE",
        "actor_source": "USER",
    }
    values.update(overrides)
    return RespaldoControl(**values)


def test_control_schema_and_tables_exist(persistent_test_engine):
    inspector = inspect(persistent_test_engine)

    assert CONTROL_SCHEMA in inspector.get_schema_names()
    assert set(inspector.get_table_names(schema=CONTROL_SCHEMA)) == EXPECTED_TABLES


def test_control_foreign_keys_never_reference_public(persistent_test_engine):
    inspector = inspect(persistent_test_engine)
    expected_foreign_keys = {
        ("operaciones_respaldo", "id_respaldo", "respaldos", "id_respaldo"),
        ("operaciones_respaldo", "id_respaldo_seguridad", "respaldos", "id_respaldo"),
        ("validaciones_respaldo", "id_respaldo", "respaldos", "id_respaldo"),
        ("confirmaciones_restauracion", "id_respaldo", "respaldos", "id_respaldo"),
        ("estado_sistema", "id_operacion", "operaciones_respaldo", "id_operacion"),
        ("workers_respaldo", "id_operacion_actual", "operaciones_respaldo", "id_operacion"),
        ("tickets_descarga", "id_respaldo", "respaldos", "id_respaldo"),
    }
    actual_foreign_keys = set()

    for table_name in EXPECTED_TABLES:
        for foreign_key in inspector.get_foreign_keys(table_name, schema=CONTROL_SCHEMA):
            assert foreign_key["referred_schema"] == CONTROL_SCHEMA
            assert foreign_key["referred_table"] in EXPECTED_TABLES
            actual_foreign_keys.update(
                (
                    table_name,
                    constrained_column,
                    foreign_key["referred_table"],
                    referred_column,
                )
                for constrained_column, referred_column in zip(
                    foreign_key["constrained_columns"],
                    foreign_key["referred_columns"],
                    strict=True,
                )
            )

    assert actual_foreign_keys == expected_foreign_keys


def test_internal_foreign_keys_accept_existing_backup(db_session):
    respaldo = _respaldo()
    db_session.add(respaldo)
    db_session.flush()
    now = datetime.now(UTC)
    operacion = OperacionRespaldoControl(
        tipo="RESTAURACION",
        estado="PENDIENTE",
        id_respaldo=respaldo.id_respaldo,
        id_respaldo_seguridad=respaldo.id_respaldo,
        actor_source="USER",
    )
    db_session.add(operacion)
    db_session.flush()
    db_session.add_all(
        [
            ValidacionRespaldoControl(
                id_respaldo=respaldo.id_respaldo,
                sha256="a" * 64,
                estado="VALIDO",
                created_at=now,
                expires_at=now + timedelta(hours=1),
            ),
            ConfirmacionRestauracionControl(
                id_respaldo=respaldo.id_respaldo,
                token_hash="b" * 64,
                confirmation_phrase_hash="c" * 64,
                created_at=now,
                expires_at=now + timedelta(minutes=5),
            ),
            TicketDescargaControl(
                id_respaldo=respaldo.id_respaldo,
                token_hash="d" * 64,
                created_at=now,
                expires_at=now + timedelta(minutes=1),
            ),
            EstadoSistemaControl(
                clave="MANTENIMIENTO_RESTAURACION",
                activo=True,
                id_operacion=operacion.id_operacion,
                mensaje_publico="Restauración en curso",
                updated_at=now,
            ),
            WorkerRespaldoControl(
                worker_id=f"worker-{uuid4().hex}",
                started_at=now,
                last_heartbeat_at=now,
                estado="OCUPADO",
                id_operacion_actual=operacion.id_operacion,
            ),
        ]
    )

    db_session.flush()


def test_internal_backup_foreign_key_rejects_missing_backup(db_session):
    db_session.add(
        ValidacionRespaldoControl(
            id_respaldo=uuid4(),
            sha256="f" * 64,
            estado="VALIDO",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_internal_operation_foreign_key_rejects_missing_operation(db_session):
    db_session.add(
        EstadoSistemaControl(
            clave="MANTENIMIENTO_RESTAURACION",
            activo=True,
            id_operacion=uuid4(),
            mensaje_publico="Restauración en curso",
            updated_at=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


@pytest.mark.parametrize(
    "overrides",
    [
        {"size_bytes": -1},
        {"table_count": -1},
        {"row_count": -1},
        {"format_version": 0},
    ],
)
def test_backup_numeric_constraints_reject_invalid_values(db_session, overrides):
    db_session.add(_respaldo(**overrides))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_actor_source_constraint_rejects_invalid_value(db_session):
    db_session.add(_respaldo(actor_source="UNKNOWN"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_backup_filename_is_unique(db_session):
    first = _respaldo()
    duplicate = _respaldo(nombre_archivo=first.nombre_archivo)
    db_session.add(first)
    db_session.flush()
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_download_token_hash_is_unique(db_session):
    respaldo = _respaldo()
    db_session.add(respaldo)
    db_session.flush()
    now = datetime.now(UTC)
    values = {
        "id_respaldo": respaldo.id_respaldo,
        "token_hash": "e" * 64,
        "created_at": now,
        "expires_at": now + timedelta(minutes=1),
    }
    db_session.add(TicketDescargaControl(**values))
    db_session.flush()
    db_session.add(TicketDescargaControl(**values))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_confirmation_token_hash_is_unique(db_session):
    respaldo = _respaldo()
    db_session.add(respaldo)
    db_session.flush()
    now = datetime.now(UTC)
    common = {
        "id_respaldo": respaldo.id_respaldo,
        "token_hash": "f" * 64,
        "confirmation_phrase_hash": "a" * 64,
        "created_at": now,
        "expires_at": now + timedelta(minutes=5),
    }
    db_session.add(ConfirmacionRestauracionControl(**common))
    db_session.flush()
    db_session.add(ConfirmacionRestauracionControl(**common))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_only_one_destructive_operation_can_be_active(db_session):
    common = {
        "estado": "PENDIENTE",
        "actor_source": "USER",
    }
    db_session.add(OperacionRespaldoControl(tipo="RESTAURACION", **common))
    db_session.flush()
    db_session.add(OperacionRespaldoControl(tipo="RECUPERACION", **common))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_maintenance_state_persists_without_public_dependencies(db_session):
    persisted = set_estado_mantenimiento(
        db_session,
        activo=True,
        mensaje_publico="Restauración en curso",
    )

    db_session.expire_all()
    loaded = get_estado_mantenimiento(db_session)
    assert loaded is not None
    assert loaded.clave == "MANTENIMIENTO_RESTAURACION"
    assert loaded.activo is True
    assert loaded.mensaje_publico == "Restauración en curso"
    assert persisted.id_operacion is None
    assert db_session.query(EstadoSistemaControl).count() == 1


def test_schema_bootstrap_is_idempotent(persistent_test_engine, monkeypatch):
    from app.bootstrap import schema_bootstrap

    monkeypatch.setattr(schema_bootstrap, "engine", persistent_test_engine)

    schema_bootstrap.run_schema_bootstrap()
    schema_bootstrap.run_schema_bootstrap()

    inspector = inspect(persistent_test_engine)
    assert set(inspector.get_table_names(schema=CONTROL_SCHEMA)) == EXPECTED_TABLES
