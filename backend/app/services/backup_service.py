"""Generacion coordinada de respaldos logicos PostgreSQL.

La fase 3B crea el dump y su lista TOC, pero nunca ejecuta una restauracion.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection, URL, make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.crud_respaldos import create_respaldo, update_respaldo
from app.db.database import engine
from app.services.backup_package import (
    BackupPackageError,
    PackageValidationLimits,
    create_backup_package,
    generate_backup_filename,
    read_backup_manifest,
    sha256_file,
)


PG_DUMP_NOT_FOUND = "PG_DUMP_NOT_FOUND"
PG_DUMP_VERSION_INCOMPATIBLE = "PG_DUMP_VERSION_INCOMPATIBLE"
PG_RESTORE_NOT_FOUND = "PG_RESTORE_NOT_FOUND"
PG_RESTORE_VERSION_INCOMPATIBLE = "PG_RESTORE_VERSION_INCOMPATIBLE"
SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
TABLE_COUNT_FAILED = "TABLE_COUNT_FAILED"
PG_DUMP_FAILED = "PG_DUMP_FAILED"
RESTORE_LIST_FAILED = "RESTORE_LIST_FAILED"
UNEXPECTED_TOC_OBJECT = "UNEXPECTED_TOC_OBJECT"
PACKAGE_BUILD_FAILED = "PACKAGE_BUILD_FAILED"
STORAGE_ERROR = "STORAGE_ERROR"
POSTGRES_SERVER_VERSION_INCOMPATIBLE = "POSTGRES_SERVER_VERSION_INCOMPATIBLE"
BACKUP_INTERNAL_ERROR = "BACKUP_INTERNAL_ERROR"

POSTGRESQL_MAJOR = 16
_VERSION_PATTERN = re.compile(r"\b(\d+)(?:\.\d+)*\b")
_TOC_LINE_PATTERN = re.compile(r"^\s*\d+;\s+\d+\s+\d+\s+(.+)$")
_TOC_TYPES = (
    "SEQUENCE OWNED BY",
    "SEQUENCE SET",
    "TABLE DATA",
    "FK CONSTRAINT",
    "CONSTRAINT",
    "COMMENT",
    "SEQUENCE",
    "DEFAULT",
    "INDEX",
    "TABLE",
    "SCHEMA",
)


class BackupGenerationError(Exception):
    """Error sanitizado y estable del flujo de generacion."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message[:500]


@dataclass(frozen=True)
class PostgreSQLTool:
    executable: str
    version: str


@dataclass(frozen=True)
class DatabaseInventory:
    tables: frozenset[str]
    sequences: frozenset[str]
    indexes: frozenset[str]
    constraints: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class BackupGenerationResult:
    backup_id: UUID
    package_path: Path
    package_sha256: str
    manifest: dict[str, Any]


def _package_limits(config: Any) -> PackageValidationLimits:
    return PackageValidationLimits(
        max_entries=config.backup_max_package_entries,
        max_package_bytes=config.backup_max_upload_bytes,
        max_uncompressed_bytes=config.backup_max_uncompressed_bytes,
        max_compression_ratio=config.backup_max_compression_ratio,
        stream_chunk_bytes=config.backup_stream_chunk_bytes,
    )


def _find_tool(name: str, *, missing_code: str, version_code: str) -> PostgreSQLTool:
    executable = shutil.which(name)
    if executable is None:
        raise BackupGenerationError(missing_code, f"{name} no esta disponible")
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupGenerationError(version_code, f"No fue posible validar {name}") from exc
    version_output = (completed.stdout or "").strip()
    match = _VERSION_PATTERN.search(version_output)
    if completed.returncode != 0 or match is None or int(match.group(1)) != POSTGRESQL_MAJOR:
        raise BackupGenerationError(version_code, f"Version incompatible de {name}")
    return PostgreSQLTool(executable=executable, version=match.group(0))


def validate_postgresql_tools() -> tuple[PostgreSQLTool, PostgreSQLTool]:
    pg_dump = _find_tool(
        "pg_dump",
        missing_code=PG_DUMP_NOT_FOUND,
        version_code=PG_DUMP_VERSION_INCOMPATIBLE,
    )
    pg_restore = _find_tool(
        "pg_restore",
        missing_code=PG_RESTORE_NOT_FOUND,
        version_code=PG_RESTORE_VERSION_INCOMPATIBLE,
    )
    return pg_dump, pg_restore


def _connection_parameters(database_url: str) -> tuple[list[str], dict[str, str]]:
    url: URL = make_url(database_url)
    if url.get_backend_name() != "postgresql" or not url.database:
        raise BackupGenerationError(SNAPSHOT_FAILED, "Configuracion PostgreSQL invalida")
    args = ["--dbname", url.database]
    if url.host:
        args.extend(["--host", url.host])
    if url.port:
        args.extend(["--port", str(url.port)])
    if url.username:
        args.extend(["--username", url.username])
    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = url.password
    return args, environment


def _load_inventory(connection: Connection) -> DatabaseInventory:
    tables = frozenset(
        row[0]
        for row in connection.execute(
            text(
                "SELECT c.relname FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') "
                "ORDER BY c.relname"
            )
        )
    )
    sequences = frozenset(
        row[0]
        for row in connection.execute(
            text(
                "SELECT c.relname FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind = 'S' ORDER BY c.relname"
            )
        )
    )
    indexes = frozenset(
        row[0]
        for row in connection.execute(
            text(
                "SELECT indexname FROM pg_catalog.pg_indexes "
                "WHERE schemaname = 'public' ORDER BY indexname"
            )
        )
    )
    constraints = frozenset(
        (row[0], row[1])
        for row in connection.execute(
            text(
                "SELECT c.relname, con.conname FROM pg_catalog.pg_constraint con "
                "JOIN pg_catalog.pg_class c ON c.oid = con.conrelid "
                "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' ORDER BY c.relname, con.conname"
            )
        )
    )
    return DatabaseInventory(tables, sequences, indexes, constraints)


def export_snapshot(connection: Connection) -> str:
    try:
        connection.exec_driver_sql(
            "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        )
        snapshot_id = connection.execute(text("SELECT pg_export_snapshot()")).scalar_one()
    except Exception as exc:
        raise BackupGenerationError(SNAPSHOT_FAILED, "No fue posible exportar el snapshot") from exc
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise BackupGenerationError(SNAPSHOT_FAILED, "Snapshot PostgreSQL invalido")
    return snapshot_id


def get_postgres_server_version(connection: Connection) -> str:
    try:
        raw_version = connection.exec_driver_sql("SHOW server_version_num").scalar_one()
        version_number = int(raw_version)
    except Exception as exc:
        raise BackupGenerationError(
            POSTGRES_SERVER_VERSION_INCOMPATIBLE,
            "No fue posible validar la version del servidor PostgreSQL",
        ) from exc
    major = version_number // 10_000
    if major != POSTGRESQL_MAJOR:
        raise BackupGenerationError(
            POSTGRES_SERVER_VERSION_INCOMPATIBLE,
            "Version incompatible del servidor PostgreSQL",
        )
    minor = version_number % 10_000
    return f"{major}.{minor}"


def count_public_tables(
    connection: Connection,
    inventory: DatabaseInventory,
) -> list[dict[str, Any]]:
    preparer = connection.dialect.identifier_preparer
    counts: list[dict[str, Any]] = []
    try:
        for table_name in sorted(inventory.tables):
            quoted_schema = preparer.quote("public")
            quoted_table = preparer.quote(table_name)
            row_count = connection.exec_driver_sql(
                f"SELECT count(*) FROM {quoted_schema}.{quoted_table}"
            ).scalar_one()
            counts.append({"schema": "public", "name": table_name, "row_count": int(row_count)})
    except Exception as exc:
        raise BackupGenerationError(TABLE_COUNT_FAILED, "No fue posible contar las tablas") from exc
    return counts


def _run_pg_dump(
    tool: PostgreSQLTool,
    *,
    connection_args: Sequence[str],
    environment: Mapping[str, str],
    snapshot_id: str,
    dump_path: Path,
) -> None:
    args = [
        tool.executable,
        "--format=custom",
        "--schema=public",
        "--no-owner",
        "--no-privileges",
        f"--snapshot={snapshot_id}",
        f"--file={dump_path}",
        *connection_args,
    ]
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            args,
            env=dict(environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        process.communicate()
        if process.returncode != 0:
            raise BackupGenerationError(PG_DUMP_FAILED, "pg_dump no pudo generar el respaldo")
    except BackupGenerationError:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupGenerationError(PG_DUMP_FAILED, "No fue posible ejecutar pg_dump") from exc
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def _split_toc_entry(line: str) -> tuple[str, list[str]]:
    match = _TOC_LINE_PATTERN.match(line)
    if match is None:
        raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Entrada TOC invalida")
    tail = match.group(1)
    for object_type in _TOC_TYPES:
        prefix = f"{object_type} "
        if tail.startswith(prefix):
            return object_type, tail[len(prefix):].split()
    raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Objeto TOC no permitido")


def validate_restore_toc(
    toc_output: str,
    inventory: DatabaseInventory,
) -> list[str]:
    approved: list[str] = []
    for raw_line in toc_output.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith(";"):
            approved.append(line)
            continue
        object_type, fields = _split_toc_entry(line)
        if object_type == "SCHEMA":
            if len(fields) < 2 or fields[0] != "-" or fields[1] != "public":
                raise BackupGenerationError(
                    UNEXPECTED_TOC_OBJECT, "Schema TOC inesperado"
                )
            approved.append(line)
            continue
        if object_type == "COMMENT":
            if (
                len(fields) != 4
                or fields[0] != "-"
                or fields[1] != "SCHEMA"
                or fields[2] != "public"
            ):
                raise BackupGenerationError(
                    UNEXPECTED_TOC_OBJECT, "Comentario TOC inesperado"
                )
            approved.append(line)
            continue
        if len(fields) < 2 or fields[0] != "public":
            raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Objeto fuera de public")
        name = fields[1]
        if object_type in {"TABLE", "TABLE DATA"} and name not in inventory.tables:
            raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Tabla TOC inesperada")
        if object_type in {"SEQUENCE", "SEQUENCE SET", "SEQUENCE OWNED BY"}:
            if name not in inventory.sequences:
                raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Secuencia TOC inesperada")
        if object_type == "INDEX" and name not in inventory.indexes:
            raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Indice TOC inesperado")
        if object_type in {"CONSTRAINT", "FK CONSTRAINT"}:
            if len(fields) < 3 or (name, fields[2]) not in inventory.constraints:
                raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Constraint TOC inesperado")
        if object_type == "DEFAULT" and name not in inventory.tables:
            raise BackupGenerationError(UNEXPECTED_TOC_OBJECT, "Default TOC inesperado")
        approved.append(line)
    return approved


def _generate_restore_list(
    tool: PostgreSQLTool,
    *,
    dump_path: Path,
    restore_list_path: Path,
    inventory: DatabaseInventory,
) -> None:
    try:
        completed = subprocess.run(
            [tool.executable, "--list", str(dump_path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupGenerationError(RESTORE_LIST_FAILED, "No fue posible ejecutar pg_restore") from exc
    if completed.returncode != 0:
        raise BackupGenerationError(RESTORE_LIST_FAILED, "pg_restore no pudo listar el dump")
    approved_lines = validate_restore_toc(completed.stdout or "", inventory)
    try:
        restore_list_path.write_text("\n".join(approved_lines) + "\n", encoding="utf-8")
    except OSError as exc:
        raise BackupGenerationError(STORAGE_ERROR, "No fue posible escribir restore.list") from exc


def _mark_failed(db: Session, respaldo: Any, error: BackupGenerationError) -> None:
    update_respaldo(
        db,
        respaldo,
        estado="FALLIDO",
        completed_at=datetime.now().astimezone(),
        error_codigo=error.code,
        error_detalle=error.public_message,
    )


def _cleanup_connection(connection: Connection) -> None:
    try:
        connection.rollback()
    except Exception:
        pass
    try:
        connection.close()
    except Exception:
        pass


def generate_logical_backup(
    db: Session,
    *,
    trigger: str,
    application_version: str,
    actor_source: str = "SYSTEM",
    actor_original_id: str | None = None,
    actor_username_snapshot: str | None = None,
    database_engine: Engine = engine,
    config: Any = settings,
) -> BackupGenerationResult:
    backup_id = uuid4()
    created_at = datetime.now().astimezone()
    filename = generate_backup_filename(created_at=created_at, backup_id=backup_id)
    respaldo = create_respaldo(
        db,
        id_respaldo=backup_id,
        nombre_archivo=filename,
        ruta_relativa=filename,
        origen=trigger,
        estado="GENERANDO",
        actor_source=actor_source,
        actor_original_id=actor_original_id,
        actor_username_snapshot=actor_username_snapshot,
        application_version=application_version,
        created_at=created_at,
        started_at=created_at,
    )
    work_dir: Path | None = None
    connection: Connection | None = None
    try:
        pg_dump, pg_restore = validate_postgresql_tools()
        temp_root = Path(config.backup_temp_dir)
        storage_root = Path(config.backup_storage_dir)
        temp_root.mkdir(parents=True, exist_ok=True)
        storage_root.mkdir(parents=True, exist_ok=True)
        work_dir = Path(tempfile.mkdtemp(prefix="backup-", dir=temp_root))
        dump_path = work_dir / "database.dump"
        restore_list_path = work_dir / "restore.list"
        connection_args, environment = _connection_parameters(config.database_url)

        try:
            connection = database_engine.connect()
        except Exception as exc:
            raise BackupGenerationError(
                SNAPSHOT_FAILED, "No fue posible abrir la conexion de snapshot"
            ) from exc
        snapshot_id = export_snapshot(connection)
        postgres_server_version = get_postgres_server_version(connection)
        try:
            inventory = _load_inventory(connection)
        except BackupGenerationError:
            raise
        except Exception as exc:
            raise BackupGenerationError(
                TABLE_COUNT_FAILED, "No fue posible enumerar las tablas"
            ) from exc
        table_counts = count_public_tables(connection, inventory)
        try:
            _run_pg_dump(
                pg_dump,
                connection_args=connection_args,
                environment=environment,
                snapshot_id=snapshot_id,
                dump_path=dump_path,
            )
        finally:
            _cleanup_connection(connection)
            connection = None

        _generate_restore_list(
            pg_restore,
            dump_path=dump_path,
            restore_list_path=restore_list_path,
            inventory=inventory,
        )
        package_path = create_backup_package(
            database_dump=dump_path,
            restore_list=restore_list_path,
            destination_dir=storage_root,
            backup_id=backup_id,
            created_at=created_at,
            trigger=trigger,
            application_name=config.app_name,
            application_version=application_version,
            dump_tool_version=pg_dump.version,
            tables=table_counts,
            limits=_package_limits(config),
        )
        manifest = read_backup_manifest(package_path, limits=_package_limits(config))
        package_hash = sha256_file(
            package_path, chunk_size=config.backup_stream_chunk_bytes
        )
        total_rows = sum(item["row_count"] for item in table_counts)
        update_respaldo(
            db,
            respaldo,
            estado="DISPONIBLE",
            sha256=package_hash,
            size_bytes=package_path.stat().st_size,
            table_count=len(table_counts),
            row_count=total_rows,
            manifest_json=manifest,
            postgres_version=postgres_server_version,
            application_version=application_version,
            completed_at=datetime.now().astimezone(),
            validated_at=datetime.now().astimezone(),
            error_codigo=None,
            error_detalle=None,
        )
        return BackupGenerationResult(backup_id, package_path, package_hash, manifest)
    except BackupGenerationError as error:
        _mark_failed(db, respaldo, error)
        raise
    except BackupPackageError as exc:
        error = BackupGenerationError(PACKAGE_BUILD_FAILED, "No fue posible construir el paquete")
        _mark_failed(db, respaldo, error)
        raise error from exc
    except OSError as exc:
        error = BackupGenerationError(STORAGE_ERROR, "No fue posible usar el almacenamiento")
        _mark_failed(db, respaldo, error)
        raise error from exc
    except Exception as exc:
        error = BackupGenerationError(BACKUP_INTERNAL_ERROR, "Error interno del respaldo")
        _mark_failed(db, respaldo, error)
        raise error from exc
    finally:
        try:
            if connection is not None:
                _cleanup_connection(connection)
        finally:
            if work_dir is not None:
                shutil.rmtree(work_dir, ignore_errors=True)


__all__ = [
    "BACKUP_INTERNAL_ERROR",
    "PACKAGE_BUILD_FAILED",
    "PG_DUMP_FAILED",
    "PG_DUMP_NOT_FOUND",
    "PG_DUMP_VERSION_INCOMPATIBLE",
    "PG_RESTORE_NOT_FOUND",
    "PG_RESTORE_VERSION_INCOMPATIBLE",
    "POSTGRES_SERVER_VERSION_INCOMPATIBLE",
    "RESTORE_LIST_FAILED",
    "SNAPSHOT_FAILED",
    "STORAGE_ERROR",
    "TABLE_COUNT_FAILED",
    "UNEXPECTED_TOC_OBJECT",
    "BackupGenerationError",
    "BackupGenerationResult",
    "DatabaseInventory",
    "PostgreSQLTool",
    "count_public_tables",
    "export_snapshot",
    "generate_logical_backup",
    "get_postgres_server_version",
    "validate_postgresql_tools",
    "validate_restore_toc",
]
