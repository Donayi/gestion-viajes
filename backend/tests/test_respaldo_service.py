from pathlib import Path
from types import SimpleNamespace

import pytest

from app.crud import crud_respaldos
from app.services import backup_service as service


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class RowsResult:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)


class FakePreparer:
    @staticmethod
    def quote(value):
        return f'"{value}"'


class FakeConnection:
    def __init__(self, *, rollback_error=False, close_error=False):
        self.dialect = SimpleNamespace(identifier_preparer=FakePreparer())
        self.commands = []
        self.rolled_back = False
        self.closed = False
        self.rollback_error = rollback_error
        self.close_error = close_error

    def exec_driver_sql(self, statement):
        self.commands.append(statement)
        if statement.startswith("SELECT count"):
            return ScalarResult(7 if '"viajes"' in statement else 3)
        if statement == "SHOW server_version_num":
            return ScalarResult("160004")
        return ScalarResult(None)

    def execute(self, statement):
        sql = str(statement)
        self.commands.append(sql)
        if "pg_export_snapshot" in sql:
            return ScalarResult("00000003-0000001B-1")
        return RowsResult([])

    def rollback(self):
        self.rolled_back = True
        if self.rollback_error:
            raise RuntimeError("rollback failed")

    def close(self):
        self.closed = True
        if self.close_error:
            raise RuntimeError("close failed")


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return self.connection


def _config(tmp_path):
    return SimpleNamespace(
        backup_temp_dir=tmp_path / "work",
        backup_storage_dir=tmp_path / "storage",
        backup_max_package_entries=16,
        backup_max_upload_bytes=10_000_000,
        backup_max_uncompressed_bytes=10_000_000,
        backup_max_compression_ratio=100.0,
        backup_stream_chunk_bytes=128,
        database_url="postgresql+psycopg://backup_user:super-secret@db:5432/logistica",
        app_name="Gestion de Viajes",
    )


def _inventory():
    return service.DatabaseInventory(
        tables=frozenset({"viajes"}),
        sequences=frozenset({"viajes_id_seq"}),
        indexes=frozenset({"ix_viajes"}),
        constraints=frozenset(
            {("viajes", "viajes_pkey"), ("viajes", "viajes_cliente_fkey")}
        ),
    )


def _valid_toc():
    return "\n".join(
        [
            "; Archive created at 2026-08-08",
            "7; 2615 2200 SCHEMA - public owner",
            "3848; 0 0 COMMENT - SCHEMA public pg_database_owner",
            "1; 1259 1 TABLE public viajes owner",
            "2; 0 1 TABLE DATA public viajes owner",
            "8; 2604 5 DEFAULT public viajes id owner",
            "3; 1259 2 SEQUENCE public viajes_id_seq owner",
            "9; 0 0 SEQUENCE OWNED BY public viajes_id_seq owner",
            "4; 0 0 SEQUENCE SET public viajes_id_seq owner",
            "5; 1259 3 INDEX public ix_viajes owner",
            "6; 2606 4 CONSTRAINT public viajes viajes_pkey owner",
            "10; 2606 6 FK CONSTRAINT public viajes viajes_cliente_fkey owner",
        ]
    )


def test_pg_dump_compatible_version(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda name: f"/tools/{name}")
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="pg_dump (PostgreSQL) 16.4\n", stderr=""
        ),
    )

    tool = service._find_tool(
        "pg_dump",
        missing_code=service.PG_DUMP_NOT_FOUND,
        version_code=service.PG_DUMP_VERSION_INCOMPATIBLE,
    )

    assert tool.executable == "/tools/pg_dump"
    assert tool.version == "16.4"


def test_pg_dump_not_found(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda name: None)

    with pytest.raises(service.BackupGenerationError) as captured:
        service._find_tool(
            "pg_dump",
            missing_code=service.PG_DUMP_NOT_FOUND,
            version_code=service.PG_DUMP_VERSION_INCOMPATIBLE,
        )

    assert captured.value.code == service.PG_DUMP_NOT_FOUND


def test_pg_dump_incompatible_version(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda name: "/tools/pg_dump")
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="pg_dump (PostgreSQL) 15.8\n", stderr=""
        ),
    )

    with pytest.raises(service.BackupGenerationError) as captured:
        service._find_tool(
            "pg_dump",
            missing_code=service.PG_DUMP_NOT_FOUND,
            version_code=service.PG_DUMP_VERSION_INCOMPATIBLE,
        )

    assert captured.value.code == service.PG_DUMP_VERSION_INCOMPATIBLE


def test_pg_restore_not_found(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda name: None)

    with pytest.raises(service.BackupGenerationError) as captured:
        service._find_tool(
            "pg_restore",
            missing_code=service.PG_RESTORE_NOT_FOUND,
            version_code=service.PG_RESTORE_VERSION_INCOMPATIBLE,
        )

    assert captured.value.code == service.PG_RESTORE_NOT_FOUND


def test_pg_restore_incompatible_version(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda name: "/tools/pg_restore")
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="pg_restore (PostgreSQL) 15.8\n", stderr=""
        ),
    )

    with pytest.raises(service.BackupGenerationError) as captured:
        service._find_tool(
            "pg_restore",
            missing_code=service.PG_RESTORE_NOT_FOUND,
            version_code=service.PG_RESTORE_VERSION_INCOMPATIBLE,
        )

    assert captured.value.code == service.PG_RESTORE_VERSION_INCOMPATIBLE


def test_snapshot_is_exported_from_read_only_repeatable_read_transaction():
    connection = FakeConnection()

    snapshot = service.export_snapshot(connection)

    assert snapshot == "00000003-0000001B-1"
    assert connection.commands[0] == (
        "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    )
    assert "pg_export_snapshot" in connection.commands[1]


def test_postgres_server_version_is_read_and_sanitized():
    assert service.get_postgres_server_version(FakeConnection()) == "16.4"


def test_postgres_server_version_rejects_incompatible_major():
    connection = FakeConnection()
    original = connection.exec_driver_sql

    def incompatible_version(statement):
        if statement == "SHOW server_version_num":
            return ScalarResult("150008")
        return original(statement)

    connection.exec_driver_sql = incompatible_version

    with pytest.raises(service.BackupGenerationError) as captured:
        service.get_postgres_server_version(connection)

    assert captured.value.code == service.POSTGRES_SERVER_VERSION_INCOMPATIBLE


def test_counts_all_allowlisted_public_tables():
    connection = FakeConnection()
    inventory = service.DatabaseInventory(
        tables=frozenset({"usuarios", "viajes"}),
        sequences=frozenset(),
        indexes=frozenset(),
        constraints=frozenset(),
    )

    counts = service.count_public_tables(connection, inventory)

    assert counts == [
        {"schema": "public", "name": "usuarios", "row_count": 3},
        {"schema": "public", "name": "viajes", "row_count": 7},
    ]


def test_pg_dump_receives_snapshot_and_password_only_in_environment(monkeypatch, tmp_path):
    captured = {}

    class FakeProcess:
        returncode = 0

        def __init__(self, args, **kwargs):
            captured["args"] = args
            captured["environment"] = kwargs["env"]

        def communicate(self):
            return "", ""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(service.subprocess, "Popen", FakeProcess)
    connection_args, environment = service._connection_parameters(
        "postgresql+psycopg://backup_user:super-secret@db:5432/logistica"
    )

    service._run_pg_dump(
        service.PostgreSQLTool("/tools/pg_dump", "16.4"),
        connection_args=connection_args,
        environment=environment,
        snapshot_id="snapshot-123",
        dump_path=tmp_path / "database.dump",
    )

    assert "--snapshot=snapshot-123" in captured["args"]
    assert "--format=custom" in captured["args"]
    assert "--schema=public" in captured["args"]
    assert "--no-owner" in captured["args"]
    assert "--no-privileges" in captured["args"]
    assert all("super-secret" not in argument for argument in captured["args"])
    assert captured["environment"]["PGPASSWORD"] == "super-secret"


def test_pg_dump_stderr_secret_is_not_exposed_or_persisted(monkeypatch, tmp_path):
    class FailedProcess:
        returncode = 1

        def __init__(self, *args, **kwargs):
            pass

        def communicate(self):
            return "", "fatal: password=super-secret"

        def poll(self):
            return self.returncode

    monkeypatch.setattr(service.subprocess, "Popen", FailedProcess)
    with pytest.raises(service.BackupGenerationError) as captured:
        service._run_pg_dump(
            service.PostgreSQLTool("/tools/pg_dump", "16.4"),
            connection_args=["--dbname", "logistica"],
            environment={"PGPASSWORD": "super-secret"},
            snapshot_id="snapshot-123",
            dump_path=tmp_path / "database.dump",
        )

    updates = []
    monkeypatch.setattr(
        service,
        "update_respaldo",
        lambda db, respaldo, **values: updates.append(values) or respaldo,
    )
    service._mark_failed(object(), object(), captured.value)

    assert "super-secret" not in captured.value.public_message
    assert "super-secret" not in updates[-1]["error_detalle"]


def test_pg_restore_list_command_and_valid_toc(monkeypatch, tmp_path):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return SimpleNamespace(returncode=0, stdout=_valid_toc(), stderr="")

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    dump_path = tmp_path / "database.dump"
    dump_path.write_bytes(b"dummy")
    restore_path = tmp_path / "restore.list"

    service._generate_restore_list(
        service.PostgreSQLTool("/tools/pg_restore", "16.4"),
        dump_path=dump_path,
        restore_list_path=restore_path,
        inventory=_inventory(),
    )

    assert captured["args"] == ["/tools/pg_restore", "--list", str(dump_path)]
    assert "TABLE public viajes" in restore_path.read_text(encoding="utf-8")


def test_valid_toc_is_accepted():
    approved = service.validate_restore_toc(_valid_toc(), _inventory())

    assert len(approved) == 12


def test_toc_rejects_non_public_schema():
    toc = "7; 2615 2200 SCHEMA - control_respaldo owner"

    with pytest.raises(service.BackupGenerationError) as captured:
        service.validate_restore_toc(toc, _inventory())

    assert captured.value.code == service.UNEXPECTED_TOC_OBJECT


@pytest.mark.parametrize(
    "toc",
    [
        "3848; 0 0 COMMENT - SCHEMA control_respaldo owner",
        "3848; 0 0 COMMENT - TABLE public viajes owner",
    ],
)
def test_toc_rejects_comments_other_than_public_schema(toc):
    with pytest.raises(service.BackupGenerationError) as captured:
        service.validate_restore_toc(toc, _inventory())

    assert captured.value.code == service.UNEXPECTED_TOC_OBJECT


def test_toc_rejects_control_respaldo():
    toc = "1; 1259 1 TABLE control_respaldo respaldos owner"

    with pytest.raises(service.BackupGenerationError) as captured:
        service.validate_restore_toc(toc, _inventory())

    assert captured.value.code == service.UNEXPECTED_TOC_OBJECT


def test_toc_rejects_unknown_object():
    toc = "1; 1255 1 FUNCTION public funcion_desconocida() owner"

    with pytest.raises(service.BackupGenerationError) as captured:
        service.validate_restore_toc(toc, _inventory())

    assert captured.value.code == service.UNEXPECTED_TOC_OBJECT


@pytest.mark.parametrize(
    "object_type",
    ["FUNCTION", "PROCEDURE", "EXTENSION", "ACL", "OWNER", "TABLESPACE", "EVENT TRIGGER"],
)
def test_toc_rejects_forbidden_object_types(object_type):
    toc = f"1; 1 1 {object_type} public forbidden owner"

    with pytest.raises(service.BackupGenerationError) as captured:
        service.validate_restore_toc(toc, _inventory())

    assert captured.value.code == service.UNEXPECTED_TOC_OBJECT


def _prepare_orchestration(monkeypatch, tmp_path, *, fail_dump=False, connection=None):
    config = _config(tmp_path)
    connection = connection or FakeConnection()
    respaldo = SimpleNamespace(id_respaldo=None)
    updates = []
    package_calls = []

    monkeypatch.setattr(service, "create_respaldo", lambda db, **values: respaldo)
    monkeypatch.setattr(
        service,
        "update_respaldo",
        lambda db, item, **values: updates.append(values) or item,
    )
    monkeypatch.setattr(
        service,
        "validate_postgresql_tools",
        lambda: (
            service.PostgreSQLTool("/tools/pg_dump", "16.4"),
            service.PostgreSQLTool("/tools/pg_restore", "16.4"),
        ),
    )
    monkeypatch.setattr(service, "export_snapshot", lambda connection: "snapshot-123")
    monkeypatch.setattr(service, "_load_inventory", lambda connection: _inventory())
    monkeypatch.setattr(
        service,
        "count_public_tables",
        lambda connection, inventory: [
            {"schema": "public", "name": "viajes", "row_count": 7}
        ],
    )

    def fake_dump(*args, dump_path, **kwargs):
        if fail_dump:
            raise service.BackupGenerationError(
                service.PG_DUMP_FAILED,
                "pg_dump no pudo generar el respaldo",
            )
        dump_path.write_bytes(b"PGDMP dummy")

    monkeypatch.setattr(service, "_run_pg_dump", fake_dump)
    monkeypatch.setattr(
        service,
        "_generate_restore_list",
        lambda tool, *, restore_list_path, **kwargs: restore_list_path.write_text(
            _valid_toc(), encoding="utf-8"
        ),
    )

    package_path = config.backup_storage_dir / "result.dafreq-backup"

    def fake_create_package(**kwargs):
        package_calls.append(kwargs)
        package_path.write_bytes(b"portable package")
        return package_path

    monkeypatch.setattr(service, "create_backup_package", fake_create_package)
    monkeypatch.setattr(
        service,
        "read_backup_manifest",
        lambda *args, **kwargs: {"format": "dafreq-backup", "totals": {"rows": 7}},
    )
    monkeypatch.setattr(service, "sha256_file", lambda *args, **kwargs: "a" * 64)
    return config, connection, respaldo, updates, package_calls


def test_dump_failure_cleans_workdir_persists_failed_and_hides_secrets(monkeypatch, tmp_path):
    config, connection, _, updates, _ = _prepare_orchestration(
        monkeypatch, tmp_path, fail_dump=True
    )

    with pytest.raises(service.BackupGenerationError) as captured:
        service.generate_logical_backup(
            object(),
            trigger="MANUAL",
            application_version="1.0.0",
            database_engine=FakeEngine(connection),
            config=config,
        )

    assert captured.value.code == service.PG_DUMP_FAILED
    assert "super-secret" not in captured.value.public_message
    assert updates[-1]["estado"] == "FALLIDO"
    assert updates[-1]["error_codigo"] == service.PG_DUMP_FAILED
    assert "super-secret" not in updates[-1]["error_detalle"]
    assert list(config.backup_temp_dir.iterdir()) == []
    assert connection.rolled_back is True
    assert connection.closed is True


def test_success_uses_backup_package_and_persists_available(monkeypatch, tmp_path):
    config, connection, _, updates, package_calls = _prepare_orchestration(
        monkeypatch, tmp_path
    )

    result = service.generate_logical_backup(
        object(),
        trigger="MANUAL",
        application_version="1.0.0",
        database_engine=FakeEngine(connection),
        config=config,
    )

    assert result.package_sha256 == "a" * 64
    assert len(package_calls) == 1
    assert package_calls[0]["trigger"] == "MANUAL"
    assert package_calls[0]["tables"] == [
        {"schema": "public", "name": "viajes", "row_count": 7}
    ]
    assert updates[-1]["estado"] == "DISPONIBLE"
    assert updates[-1]["sha256"] == "a" * 64
    assert updates[-1]["table_count"] == 1
    assert updates[-1]["row_count"] == 7
    assert updates[-1]["manifest_json"]["format"] == "dafreq-backup"
    assert updates[-1]["postgres_version"] == "16.4"
    assert list(config.backup_temp_dir.iterdir()) == []


def test_cleanup_continues_when_rollback_and_close_fail(monkeypatch, tmp_path):
    connection = FakeConnection(rollback_error=True, close_error=True)
    config, _, _, updates, _ = _prepare_orchestration(
        monkeypatch,
        tmp_path,
        fail_dump=True,
        connection=connection,
    )

    with pytest.raises(service.BackupGenerationError) as captured:
        service.generate_logical_backup(
            object(),
            trigger="MANUAL",
            application_version="1.0.0",
            database_engine=FakeEngine(connection),
            config=config,
        )

    assert captured.value.code == service.PG_DUMP_FAILED
    assert updates[-1]["error_codigo"] == service.PG_DUMP_FAILED
    assert connection.rolled_back is True
    assert connection.closed is True
    assert list(config.backup_temp_dir.iterdir()) == []


def test_unexpected_failure_uses_internal_error_code(monkeypatch, tmp_path):
    config, connection, _, updates, _ = _prepare_orchestration(monkeypatch, tmp_path)

    def unexpected_failure(**kwargs):
        raise ValueError("unexpected internal detail")

    monkeypatch.setattr(service, "create_backup_package", unexpected_failure)

    with pytest.raises(service.BackupGenerationError) as captured:
        service.generate_logical_backup(
            object(),
            trigger="MANUAL",
            application_version="1.0.0",
            database_engine=FakeEngine(connection),
            config=config,
        )

    assert captured.value.code == service.BACKUP_INTERNAL_ERROR
    assert captured.value.public_message == "Error interno del respaldo"
    assert updates[-1]["error_codigo"] == service.BACKUP_INTERNAL_ERROR


def test_update_respaldo_allows_columns_and_rejects_non_persistable_attributes():
    calls = []
    db = SimpleNamespace(
        commit=lambda: calls.append("commit"),
        refresh=lambda item: calls.append(("refresh", item)),
    )
    respaldo = SimpleNamespace(estado="GENERANDO", metodo=lambda: None)

    updated = crud_respaldos.update_respaldo(db, respaldo, estado="DISPONIBLE")

    assert updated.estado == "DISPONIBLE"
    assert calls[0] == "commit"
    with pytest.raises(ValueError):
        crud_respaldos.update_respaldo(db, respaldo, metodo="reemplazado")
    with pytest.raises(ValueError):
        crud_respaldos.update_respaldo(db, respaldo, id_respaldo="reemplazado")
