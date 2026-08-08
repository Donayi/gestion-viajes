"""Construccion y validacion segura de paquetes portables ``.dafreq-backup``.

Este modulo no genera dumps ni ejecuta herramientas de PostgreSQL. Solo recibe
los dos artefactos de base de datos ya existentes y los encapsula en un ZIP con
un contrato estricto y verificable.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
import tempfile
import zipfile
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4


MANIFEST_PATH = "manifest.json"
DATABASE_DUMP_PATH = "database/database.dump"
RESTORE_LIST_PATH = "database/restore.list"
CHECKSUMS_PATH = "checksums/sha256sums.json"
PACKAGE_ENTRIES = frozenset(
    {MANIFEST_PATH, DATABASE_DUMP_PATH, RESTORE_LIST_PATH, CHECKSUMS_PATH}
)
CHECKSUMMED_ENTRIES = (DATABASE_DUMP_PATH, RESTORE_LIST_PATH, MANIFEST_PATH)
PACKAGE_FORMAT = "dafreq-backup"
PACKAGE_FORMAT_VERSION = 1
POSTGRESQL_SERVER_MAJOR = 16
DATABASE_DUMP_FORMAT = "custom"
DATABASE_ENCODING = "UTF8"
INVALID_ZIP = "INVALID_ZIP"
MISSING_ENTRY = "MISSING_ENTRY"
UNEXPECTED_ENTRY = "UNEXPECTED_ENTRY"
DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
UNSAFE_PATH = "UNSAFE_PATH"
SYMLINK_ENTRY = "SYMLINK_ENTRY"
DIRECTORY_ENTRY = "DIRECTORY_ENTRY"
TOO_MANY_ENTRIES = "TOO_MANY_ENTRIES"
PACKAGE_TOO_LARGE = "PACKAGE_TOO_LARGE"
UNCOMPRESSED_SIZE_EXCEEDED = "UNCOMPRESSED_SIZE_EXCEEDED"
COMPRESSION_RATIO_EXCEEDED = "COMPRESSION_RATIO_EXCEEDED"
INVALID_MANIFEST = "INVALID_MANIFEST"
UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
UNSUPPORTED_FORMAT_VERSION = "UNSUPPORTED_FORMAT_VERSION"
UNSUPPORTED_POSTGRES_VERSION = "UNSUPPORTED_POSTGRES_VERSION"
UNSUPPORTED_DUMP_FORMAT = "UNSUPPORTED_DUMP_FORMAT"
INCOMPATIBLE_SCOPE = "INCOMPATIBLE_SCOPE"
CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
UNSUPPORTED_ZIP_FEATURE = "UNSUPPORTED_ZIP_FEATURE"
PACKAGE_UNREADABLE = "PACKAGE_UNREADABLE"
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_JSON_ENTRY_BYTES = 16 * 1024 * 1024
_SAFE_FILENAME_PATTERN = re.compile(
    r"^dafreq-backup-\d{8}T\d{6}[+-]\d{4}-[0-9a-f]{8}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.dafreq-backup$"
)


class BackupPackageError(Exception):
    """Base para errores internos del contenedor de respaldo."""


class BackupPackageBuildError(BackupPackageError):
    """El paquete no pudo construirse de forma segura."""


class BackupPackageValidationError(BackupPackageError):
    """El paquete no cumple el contrato aprobado."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PackageValidationLimits:
    max_entries: int
    max_package_bytes: int
    max_uncompressed_bytes: int
    max_compression_ratio: float
    stream_chunk_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_entries <= 0 or self.max_package_bytes <= 0:
            raise ValueError("Los limites del paquete deben ser positivos")
        if self.max_uncompressed_bytes <= 0 or self.max_compression_ratio <= 1:
            raise ValueError("Los limites de expansion deben ser validos")
        if self.stream_chunk_bytes <= 0:
            raise ValueError("El tamano de bloque debe ser positivo")


@dataclass(frozen=True)
class PackageValidationResult:
    valid: bool
    backup_id: UUID | None
    format_version: int | None
    manifest: dict[str, Any] | None
    package_size_bytes: int
    package_sha256: str | None
    error_code: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _configured_limits() -> PackageValidationLimits:
    # Import diferido: el componente sigue siendo utilizable sin inicializar la
    # configuracion global hasta que el consumidor solicite limites por defecto.
    from app.core.config import settings

    return PackageValidationLimits(
        max_entries=settings.backup_max_package_entries,
        max_package_bytes=settings.backup_max_upload_bytes,
        max_uncompressed_bytes=settings.backup_max_uncompressed_bytes,
        max_compression_ratio=settings.backup_max_compression_ratio,
        stream_chunk_bytes=settings.backup_stream_chunk_bytes,
    )


def generate_backup_filename(
    *,
    created_at: datetime | None = None,
    backup_id: UUID | None = None,
) -> str:
    """Genera un nombre portable con timestamp zonificado y UUID."""
    timestamp = created_at or datetime.now().astimezone()
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("created_at debe incluir zona horaria")
    identifier = backup_id or uuid4()
    offset = timestamp.strftime("%z")
    name = f"dafreq-backup-{timestamp:%Y%m%dT%H%M%S}{offset}-{identifier}.dafreq-backup"
    if not _SAFE_FILENAME_PATTERN.fullmatch(name):
        raise BackupPackageBuildError("No fue posible generar un nombre portable")
    return name


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Calcula SHA-256 sin cargar el archivo completo en memoria."""
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_manifest(
    *,
    backup_id: UUID,
    created_at: datetime,
    trigger: str,
    application_name: str,
    application_version: str,
    dump_tool_version: str,
    dump_size_bytes: int,
    dump_sha256: str,
    restore_list_size_bytes: int,
    restore_list_sha256: str,
    tables: Sequence[Mapping[str, Any]],
    package_size_bytes: int = 0,
) -> dict[str, Any]:
    """Construye el manifiesto estricto a partir de metadatos no sensibles."""
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at debe incluir zona horaria")
    table_items = [
        {
            "schema": item["schema"],
            "name": item["name"],
            "row_count": item["row_count"],
        }
        for item in tables
    ]
    return {
        "format": PACKAGE_FORMAT,
        "format_version": PACKAGE_FORMAT_VERSION,
        "backup_id": str(backup_id),
        "created_at": created_at.isoformat(),
        "trigger": trigger,
        "application": {"name": application_name, "version": application_version},
        "database": {
            "engine": "postgresql",
            "server_major": POSTGRESQL_SERVER_MAJOR,
            "dump_format": DATABASE_DUMP_FORMAT,
            "dump_tool_version": dump_tool_version,
            "encoding": DATABASE_ENCODING,
        },
        "scope": {
            "database_business_data": True,
            "backup_control_tables": False,
            "r2_objects": False,
            "r2_metadata": True,
        },
        "integrity": {
            "payload_files": [DATABASE_DUMP_PATH, RESTORE_LIST_PATH],
            "manifest_covered_by": CHECKSUMS_PATH,
            "checksums_self_hash": False,
            "package_hash": "external",
        },
        # files contiene exclusivamente payload. manifest.json se autentica en
        # sha256sums.json; este ultimo y el ZIP completo quedan fuera de toda
        # autorreferencia.
        "files": [
            {
                "path": DATABASE_DUMP_PATH,
                "size_bytes": dump_size_bytes,
                "sha256": dump_sha256,
            },
            {
                "path": RESTORE_LIST_PATH,
                "size_bytes": restore_list_size_bytes,
                "sha256": restore_list_sha256,
            },
        ],
        "tables": table_items,
        "totals": {
            "tables": len(table_items),
            "rows": sum(item["row_count"] for item in table_items),
            "package_size_bytes": package_size_bytes,
        },
    }


def build_sha256sums(
    *,
    manifest_bytes: bytes,
    dump_sha256: str,
    restore_list_sha256: str,
) -> dict[str, str]:
    """Construye el registro de hashes internos sin autorreferencias."""
    return {
        DATABASE_DUMP_PATH: dump_sha256,
        RESTORE_LIST_PATH: restore_list_sha256,
        MANIFEST_PATH: hashlib.sha256(manifest_bytes).hexdigest(),
    }


def _write_zip(
    path: Path,
    *,
    manifest_bytes: bytes,
    checksums_bytes: bytes,
    database_dump: Path,
    restore_list: Path,
) -> None:
    def stored_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        return info

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        # Metadatos fijos y ZIP_STORED hacen que package_size_bytes solo pueda
        # cambiar por la cantidad de digitos de su propia representacion.
        archive.writestr(stored_info(MANIFEST_PATH), manifest_bytes)
        archive.write(database_dump, DATABASE_DUMP_PATH)
        archive.write(restore_list, RESTORE_LIST_PATH)
        archive.writestr(stored_info(CHECKSUMS_PATH), checksums_bytes)


def create_backup_package(
    *,
    database_dump: Path,
    restore_list: Path,
    destination_dir: Path,
    backup_id: UUID,
    created_at: datetime,
    trigger: str,
    application_name: str,
    application_version: str,
    dump_tool_version: str,
    tables: Sequence[Mapping[str, Any]],
    limits: PackageValidationLimits | None = None,
) -> Path:
    """Crea, valida y publica atomicamente un paquete nuevo."""
    dump_path = Path(database_dump)
    list_path = Path(restore_list)
    target_dir = Path(destination_dir)
    if not dump_path.is_file() or not list_path.is_file():
        raise BackupPackageBuildError("Faltan artefactos de base de datos requeridos")
    if not target_dir.is_dir():
        raise BackupPackageBuildError("El directorio de destino no existe")

    active_limits = limits or _configured_limits()
    dump_hash = sha256_file(dump_path, chunk_size=active_limits.stream_chunk_bytes)
    restore_hash = sha256_file(list_path, chunk_size=active_limits.stream_chunk_bytes)
    filename = generate_backup_filename(created_at=created_at, backup_id=backup_id)
    final_path = target_dir / filename
    if final_path.exists():
        raise BackupPackageBuildError("El paquete de destino ya existe")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".dafreq-backup-", suffix=".tmp", dir=target_dir
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        declared_size = 0
        for _ in range(10):
            manifest = build_manifest(
                backup_id=backup_id,
                created_at=created_at,
                trigger=trigger,
                application_name=application_name,
                application_version=application_version,
                dump_tool_version=dump_tool_version,
                dump_size_bytes=dump_path.stat().st_size,
                dump_sha256=dump_hash,
                restore_list_size_bytes=list_path.stat().st_size,
                restore_list_sha256=restore_hash,
                tables=tables,
                package_size_bytes=declared_size,
            )
            manifest_bytes = _json_bytes(manifest)
            checksums_bytes = _json_bytes(
                build_sha256sums(
                    manifest_bytes=manifest_bytes,
                    dump_sha256=dump_hash,
                    restore_list_sha256=restore_hash,
                )
            )
            _write_zip(
                temporary_path,
                manifest_bytes=manifest_bytes,
                checksums_bytes=checksums_bytes,
                database_dump=dump_path,
                restore_list=list_path,
            )
            actual_size = temporary_path.stat().st_size
            if actual_size == declared_size:
                break
            declared_size = actual_size
        else:
            raise BackupPackageBuildError("No fue posible estabilizar el tamano del paquete")

        validation = validate_backup_package(temporary_path, limits=active_limits)
        if not validation.valid:
            raise BackupPackageBuildError("El paquete generado no supero la validacion interna")
        # os.link publica una nueva entrada de directorio de forma exclusiva:
        # falla con FileExistsError si otro proceso gano la carrera. Al estar el
        # temporal en el mismo directorio, no hay cruce de filesystem. Algunos
        # filesystems sin hard links pueden rechazar la operacion; no se intenta
        # un fallback con overwrite y la construccion falla de forma segura.
        try:
            os.link(temporary_path, final_path)
        except FileExistsError as exc:
            raise BackupPackageBuildError("El paquete de destino ya existe") from exc
        except OSError as exc:
            raise BackupPackageBuildError("No fue posible publicar el paquete sin sobrescritura") from exc
        return final_path
    finally:
        temporary_path.unlink(missing_ok=True)


def _safe_entry_name(name: str) -> bool:
    if not name or "\\" in name or "\x00" in name:
        return False
    posix_path = PurePosixPath(name)
    windows_path = PureWindowsPath(name)
    if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        return False
    return all(part not in {"", ".", ".."} for part in posix_path.parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _read_entry(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    chunk_size: int,
    max_bytes: int,
) -> bytes:
    if info.file_size > max_bytes:
        raise BackupPackageValidationError(
            INVALID_MANIFEST, "Una entrada JSON excede el tamano permitido"
        )
    content = bytearray()
    with archive.open(info, "r") as stream:
        while chunk := stream.read(chunk_size):
            content.extend(chunk)
            if len(content) > info.file_size or len(content) > max_bytes:
                raise BackupPackageValidationError(INVALID_ZIP, "Tamano de entrada invalido")
    if len(content) != info.file_size:
        raise BackupPackageValidationError(INVALID_ZIP, "Tamano de entrada inconsistente")
    return bytes(content)


def _hash_entry(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    chunk_size: int,
) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with archive.open(info, "r") as stream:
        while chunk := stream.read(chunk_size):
            size += len(chunk)
            if size > info.file_size:
                raise BackupPackageValidationError(INVALID_ZIP, "Tamano de entrada invalido")
            digest.update(chunk)
    if size != info.file_size:
        raise BackupPackageValidationError(INVALID_ZIP, "Tamano de entrada inconsistente")
    return digest.hexdigest(), size


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise BackupPackageValidationError(INVALID_MANIFEST, f"Estructura invalida en {label}")


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BackupPackageValidationError(INVALID_MANIFEST, f"Valor invalido en {label}")
    return value


def _validate_manifest(manifest: Any, *, package_size: int) -> UUID:
    if not isinstance(manifest, dict):
        raise BackupPackageValidationError(INVALID_MANIFEST, "El manifiesto no es un objeto JSON")
    _require_exact_keys(
        manifest,
        {
            "format", "format_version", "backup_id", "created_at", "trigger",
            "application", "database", "scope", "integrity", "files", "tables", "totals",
        },
        "manifest",
    )
    if manifest["format"] != PACKAGE_FORMAT:
        raise BackupPackageValidationError(UNSUPPORTED_FORMAT, "Formato de paquete incompatible")
    if type(manifest["format_version"]) is not int or manifest["format_version"] != 1:
        raise BackupPackageValidationError(
            UNSUPPORTED_FORMAT_VERSION, "Version de formato incompatible"
        )
    try:
        backup_id = UUID(str(manifest["backup_id"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise BackupPackageValidationError(INVALID_MANIFEST, "backup_id invalido") from exc
    try:
        created_at = datetime.fromisoformat(_require_text(manifest["created_at"], "created_at"))
    except ValueError as exc:
        raise BackupPackageValidationError(INVALID_MANIFEST, "created_at invalido") from exc
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise BackupPackageValidationError(INVALID_MANIFEST, "created_at sin zona horaria")
    trigger = manifest["trigger"]
    if not isinstance(trigger, str):
        raise BackupPackageValidationError(INVALID_MANIFEST, "Trigger invalido")
    if trigger not in {"MANUAL", "AUTOMATICO", "PRE_RESTAURACION", "IMPORTADO"}:
        raise BackupPackageValidationError(INVALID_MANIFEST, "Trigger incompatible")

    application = manifest["application"]
    if not isinstance(application, dict):
        raise BackupPackageValidationError(INVALID_MANIFEST, "Application invalida")
    _require_exact_keys(application, {"name", "version"}, "application")
    _require_text(application["name"], "application.name")
    _require_text(application["version"], "application.version")

    database = manifest["database"]
    if not isinstance(database, dict):
        raise BackupPackageValidationError(INVALID_MANIFEST, "Database invalida")
    _require_exact_keys(
        database,
        {"engine", "server_major", "dump_format", "dump_tool_version", "encoding"},
        "database",
    )
    if database["engine"] != "postgresql":
        raise BackupPackageValidationError(INVALID_MANIFEST, "Motor de base de datos invalido")
    if database["server_major"] != 16:
        raise BackupPackageValidationError(
            UNSUPPORTED_POSTGRES_VERSION, "Version de PostgreSQL incompatible"
        )
    if database["dump_format"] != "custom":
        raise BackupPackageValidationError(UNSUPPORTED_DUMP_FORMAT, "Formato de dump incompatible")
    if database["encoding"] != "UTF8":
        raise BackupPackageValidationError(INVALID_MANIFEST, "Encoding incompatible")
    _require_text(database["dump_tool_version"], "database.dump_tool_version")

    scope = manifest["scope"]
    expected_scope = {
        "database_business_data": True,
        "backup_control_tables": False,
        "r2_objects": False,
        "r2_metadata": True,
    }
    if not isinstance(scope, dict) or scope != expected_scope:
        raise BackupPackageValidationError(INCOMPATIBLE_SCOPE, "Scope incompatible")

    integrity = manifest["integrity"]
    expected_integrity = {
        "payload_files": [DATABASE_DUMP_PATH, RESTORE_LIST_PATH],
        "manifest_covered_by": CHECKSUMS_PATH,
        "checksums_self_hash": False,
        "package_hash": "external",
    }
    if not isinstance(integrity, dict) or integrity != expected_integrity:
        raise BackupPackageValidationError(INVALID_MANIFEST, "Contrato de integridad invalido")

    files = manifest["files"]
    if not isinstance(files, list) or len(files) != 2:
        raise BackupPackageValidationError(INVALID_MANIFEST, "Listado de archivos invalido")
    file_paths: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise BackupPackageValidationError(INVALID_MANIFEST, "Entrada invalida en files")
        _require_exact_keys(item, {"path", "size_bytes", "sha256"}, "files")
        item_path = item["path"]
        if not isinstance(item_path, str) or not item_path:
            raise BackupPackageValidationError(INVALID_MANIFEST, "Path invalido en files")
        if item_path not in {DATABASE_DUMP_PATH, RESTORE_LIST_PATH}:
            raise BackupPackageValidationError(INVALID_MANIFEST, "Ruta invalida en files")
        if item_path in file_paths:
            raise BackupPackageValidationError(INVALID_MANIFEST, "Ruta duplicada en files")
        file_paths.add(item_path)
        if type(item["size_bytes"]) is not int or item["size_bytes"] < 0:
            raise BackupPackageValidationError(INVALID_MANIFEST, "Tamano invalido en files")
        if not isinstance(item["sha256"], str) or not _HASH_PATTERN.fullmatch(item["sha256"]):
            raise BackupPackageValidationError(INVALID_MANIFEST, "SHA-256 invalido en files")
    if file_paths != {DATABASE_DUMP_PATH, RESTORE_LIST_PATH}:
        raise BackupPackageValidationError(INVALID_MANIFEST, "Falta payload en el manifiesto")

    tables = manifest["tables"]
    if not isinstance(tables, list):
        raise BackupPackageValidationError(INVALID_MANIFEST, "Listado de tablas invalido")
    calculated_rows = 0
    for item in tables:
        if not isinstance(item, dict):
            raise BackupPackageValidationError(INVALID_MANIFEST, "Entrada invalida en tables")
        _require_exact_keys(item, {"schema", "name", "row_count"}, "tables")
        _require_text(item["schema"], "tables.schema")
        _require_text(item["name"], "tables.name")
        if type(item["row_count"]) is not int or item["row_count"] < 0:
            raise BackupPackageValidationError(INVALID_MANIFEST, "Conteo invalido en tables")
        calculated_rows += item["row_count"]

    totals = manifest["totals"]
    if not isinstance(totals, dict):
        raise BackupPackageValidationError(INVALID_MANIFEST, "Totales invalidos")
    _require_exact_keys(totals, {"tables", "rows", "package_size_bytes"}, "totals")
    if totals["tables"] != len(tables) or totals["rows"] != calculated_rows:
        raise BackupPackageValidationError(INVALID_MANIFEST, "Totales inconsistentes")
    if totals["package_size_bytes"] != package_size:
        raise BackupPackageValidationError(INVALID_MANIFEST, "Tamano del paquete inconsistente")
    return backup_id


def _invalid_result(
    *, package_size: int, package_sha256: str | None, code: str, message: str
) -> PackageValidationResult:
    return PackageValidationResult(
        valid=False,
        backup_id=None,
        format_version=None,
        manifest=None,
        package_size_bytes=package_size,
        package_sha256=package_sha256,
        error_code=code,
        errors=[message],
    )


def _compression_ratio(entries: Sequence[zipfile.ZipInfo]) -> float:
    expanded_size = sum(entry.file_size for entry in entries)
    compressed_size = sum(entry.compress_size for entry in entries)
    if any(entry.file_size > 0 and entry.compress_size == 0 for entry in entries):
        return float("inf")
    if expanded_size == 0:
        return 0.0
    if compressed_size == 0:
        return float("inf")
    return expanded_size / compressed_size


def validate_backup_package(
    package_path: Path,
    *,
    limits: PackageValidationLimits | None = None,
) -> PackageValidationResult:
    """Valida un paquete sin extraerlo y devuelve un resultado sanitizado."""
    path = Path(package_path)
    active_limits = limits or _configured_limits()
    try:
        package_size = path.stat().st_size
    except OSError:
        return _invalid_result(
            package_size=0,
            package_sha256=None,
            code=PACKAGE_UNREADABLE,
            message="Paquete inaccesible",
        )
    try:
        package_hash = sha256_file(path, chunk_size=active_limits.stream_chunk_bytes)
    except OSError:
        return _invalid_result(
            package_size=package_size,
            package_sha256=None,
            code=PACKAGE_UNREADABLE,
            message="Paquete ilegible",
        )
    if package_size > active_limits.max_package_bytes:
        return _invalid_result(
            package_size=package_size,
            package_sha256=package_hash,
            code=PACKAGE_TOO_LARGE,
            message="El paquete excede el tamano permitido",
        )

    try:
        with zipfile.ZipFile(path, "r") as archive:
            entries = archive.infolist()
            if len(entries) > active_limits.max_entries:
                raise BackupPackageValidationError(
                    TOO_MANY_ENTRIES, "El paquete excede el numero de entradas permitido"
                )
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise BackupPackageValidationError(
                    DUPLICATE_ENTRY, "El paquete contiene entradas duplicadas"
                )
            for entry in entries:
                if not _safe_entry_name(entry.filename):
                    raise BackupPackageValidationError(
                        UNSAFE_PATH, "El paquete contiene una ruta insegura"
                    )
                if entry.is_dir():
                    raise BackupPackageValidationError(
                        DIRECTORY_ENTRY, "El paquete contiene directorios inesperados"
                    )
                if _is_symlink(entry):
                    raise BackupPackageValidationError(
                        SYMLINK_ENTRY, "El paquete contiene enlaces simbolicos"
                    )
            if set(names) != PACKAGE_ENTRIES:
                missing = PACKAGE_ENTRIES.difference(names)
                if missing:
                    raise BackupPackageValidationError(MISSING_ENTRY, "Faltan archivos requeridos")
                raise BackupPackageValidationError(
                    UNEXPECTED_ENTRY, "El paquete contiene archivos inesperados"
                )

            expanded_size = sum(entry.file_size for entry in entries)
            if expanded_size > active_limits.max_uncompressed_bytes:
                raise BackupPackageValidationError(
                    UNCOMPRESSED_SIZE_EXCEEDED,
                    "El paquete excede el tamano expandido permitido",
                )
            ratio = _compression_ratio(entries)
            if ratio > active_limits.max_compression_ratio:
                raise BackupPackageValidationError(
                    COMPRESSION_RATIO_EXCEEDED,
                    "El paquete excede el ratio de compresion permitido",
                )

            info_by_name = {entry.filename: entry for entry in entries}
            manifest_bytes = _read_entry(
                archive,
                info_by_name[MANIFEST_PATH],
                chunk_size=active_limits.stream_chunk_bytes,
                max_bytes=min(
                    active_limits.max_uncompressed_bytes,
                    _MAX_JSON_ENTRY_BYTES,
                ),
            )
            checksums_bytes = _read_entry(
                archive,
                info_by_name[CHECKSUMS_PATH],
                chunk_size=active_limits.stream_chunk_bytes,
                max_bytes=min(
                    active_limits.max_uncompressed_bytes,
                    _MAX_JSON_ENTRY_BYTES,
                ),
            )
            try:
                manifest = json.loads(manifest_bytes.decode("utf-8"))
                checksums = json.loads(checksums_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BackupPackageValidationError(
                    INVALID_MANIFEST, "El paquete contiene JSON invalido"
                ) from exc
            if not isinstance(checksums, dict) or set(checksums) != set(CHECKSUMMED_ENTRIES):
                raise BackupPackageValidationError(
                    CHECKSUM_MISMATCH, "Registro de checksums invalido"
                )
            actual_hashes = {
                MANIFEST_PATH: hashlib.sha256(manifest_bytes).hexdigest(),
            }
            actual_sizes = {
                MANIFEST_PATH: len(manifest_bytes),
            }
            for name in (DATABASE_DUMP_PATH, RESTORE_LIST_PATH):
                entry_hash, entry_size = _hash_entry(
                    archive,
                    info_by_name[name],
                    chunk_size=active_limits.stream_chunk_bytes,
                )
                actual_hashes[name] = entry_hash
                actual_sizes[name] = entry_size
            for name in CHECKSUMMED_ENTRIES:
                expected_hash = checksums[name]
                if not isinstance(expected_hash, str) or not _HASH_PATTERN.fullmatch(expected_hash):
                    raise BackupPackageValidationError(CHECKSUM_MISMATCH, "Checksum invalido")
                if not hmac.compare_digest(expected_hash, actual_hashes[name]):
                    raise BackupPackageValidationError(CHECKSUM_MISMATCH, "Checksum incorrecto")

            backup_id = _validate_manifest(manifest, package_size=package_size)
            manifest_files = {item["path"]: item for item in manifest["files"]}
            for name in (DATABASE_DUMP_PATH, RESTORE_LIST_PATH):
                item = manifest_files[name]
                if item["size_bytes"] != actual_sizes[name]:
                    raise BackupPackageValidationError(
                        INVALID_MANIFEST, "Tamano de archivo inconsistente"
                    )
                if not hmac.compare_digest(item["sha256"], checksums[name]):
                    raise BackupPackageValidationError(
                        CHECKSUM_MISMATCH, "Checksum de manifiesto inconsistente"
                    )
            return PackageValidationResult(
                valid=True,
                backup_id=backup_id,
                format_version=manifest["format_version"],
                manifest=manifest,
                package_size_bytes=package_size,
                package_sha256=package_hash,
            )
    except BackupPackageValidationError as exc:
        return _invalid_result(
            package_size=package_size,
            package_sha256=package_hash,
            code=exc.code,
            message="El paquete no cumple el formato de respaldo aprobado",
        )
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, zlib.error):
        return _invalid_result(
            package_size=package_size,
            package_sha256=package_hash,
            code=INVALID_ZIP,
            message="El paquete ZIP no es valido",
        )
    except (RuntimeError, NotImplementedError):
        return _invalid_result(
            package_size=package_size,
            package_sha256=package_hash,
            code=UNSUPPORTED_ZIP_FEATURE,
            message="El paquete usa una caracteristica ZIP no soportada",
        )
    except OSError:
        return _invalid_result(
            package_size=package_size,
            package_sha256=package_hash,
            code=PACKAGE_UNREADABLE,
            message="No fue posible leer el paquete",
        )


def read_backup_manifest(
    package_path: Path,
    *,
    limits: PackageValidationLimits | None = None,
) -> dict[str, Any]:
    """Devuelve el manifiesto unicamente despues de validar todo el paquete."""
    result = validate_backup_package(package_path, limits=limits)
    if not result.valid or result.manifest is None:
        raise BackupPackageValidationError(
            result.error_code or INVALID_ZIP, "El paquete no es valido"
        )
    return result.manifest


__all__ = [
    "CHECKSUM_MISMATCH",
    "CHECKSUMMED_ENTRIES",
    "CHECKSUMS_PATH",
    "COMPRESSION_RATIO_EXCEEDED",
    "DATABASE_DUMP_PATH",
    "DIRECTORY_ENTRY",
    "DUPLICATE_ENTRY",
    "INCOMPATIBLE_SCOPE",
    "INVALID_MANIFEST",
    "INVALID_ZIP",
    "MANIFEST_PATH",
    "MISSING_ENTRY",
    "PACKAGE_ENTRIES",
    "PACKAGE_TOO_LARGE",
    "PACKAGE_UNREADABLE",
    "RESTORE_LIST_PATH",
    "SYMLINK_ENTRY",
    "TOO_MANY_ENTRIES",
    "UNCOMPRESSED_SIZE_EXCEEDED",
    "UNEXPECTED_ENTRY",
    "UNSAFE_PATH",
    "UNSUPPORTED_DUMP_FORMAT",
    "UNSUPPORTED_FORMAT",
    "UNSUPPORTED_FORMAT_VERSION",
    "UNSUPPORTED_POSTGRES_VERSION",
    "UNSUPPORTED_ZIP_FEATURE",
    "BackupPackageBuildError",
    "BackupPackageError",
    "BackupPackageValidationError",
    "PackageValidationLimits",
    "PackageValidationResult",
    "build_manifest",
    "build_sha256sums",
    "create_backup_package",
    "generate_backup_filename",
    "read_backup_manifest",
    "sha256_file",
    "validate_backup_package",
]
