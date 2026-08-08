"""Validacion y staging seguro previo a una futura restauracion.

Este modulo nunca conecta con PostgreSQL ni ejecuta ``pg_restore`` en modo
restauracion. Su unica invocacion permitida es ``pg_restore --list``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from app.services.backup_package import (
    DATABASE_DUMP_PATH,
    RESTORE_LIST_PATH,
    PackageValidationLimits,
    validate_backup_package,
)
from app.services.backup_service import (
    BackupGenerationError,
    DatabaseInventory,
    validate_restore_toc,
)


PACKAGE_NOT_FOUND = "PACKAGE_NOT_FOUND"
PACKAGE_NOT_REGULAR_FILE = "PACKAGE_NOT_REGULAR_FILE"
INVALID_EXPECTED_SHA256 = "INVALID_EXPECTED_SHA256"
PACKAGE_SHA256_MISMATCH = "PACKAGE_SHA256_MISMATCH"
PACKAGE_VALIDATION_FAILED = "PACKAGE_VALIDATION_FAILED"
UNAUTHORIZED_SCOPE = "UNAUTHORIZED_SCOPE"
TEMP_ROOT_INVALID = "TEMP_ROOT_INVALID"
TEMP_PATH_ESCAPE = "TEMP_PATH_ESCAPE"
MATERIALIZATION_FAILED = "MATERIALIZATION_FAILED"
PG_RESTORE_LIST_FAILED = "PG_RESTORE_LIST_FAILED"
TOC_VALIDATION_FAILED = "TOC_VALIDATION_FAILED"
TOC_MISMATCH = "TOC_MISMATCH"
INVALID_PARAMETER = "INVALID_PARAMETER"
CLEANUP_FAILED = "CLEANUP_FAILED"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_SCOPE = {
    "database_business_data": True,
    "backup_control_tables": False,
    "r2_objects": False,
    "r2_metadata": True,
}
_LOCAL_PACKAGE_NAME = "source.dafreq-backup"
_LOCAL_DUMP_NAME = "database.dump"
_LOCAL_RESTORE_LIST_NAME = "restore.list"
_LOGGER = logging.getLogger(__name__)


class RestorePreparationError(Exception):
    """Error de dominio sanitizado de la preparacion pre-restauracion."""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message[:500]


@dataclass(frozen=True)
class PreparedRestore:
    """Artefactos validos exclusivamente dentro del bloque ``with`` propietario."""

    work_dir: Path
    database_dump_path: Path
    restore_list_path: Path
    manifest: dict
    package_sha256: str
    toc_entries: tuple[str, ...]


def _regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _validate_parameters(
    expected_sha256: str,
    pg_restore_executable: str,
    list_timeout_seconds: int,
    limits: PackageValidationLimits,
) -> None:
    if not isinstance(expected_sha256, str) or not _SHA256_PATTERN.fullmatch(
        expected_sha256
    ):
        raise RestorePreparationError(
            INVALID_EXPECTED_SHA256,
            "El SHA-256 esperado no es valido",
        )
    if not isinstance(pg_restore_executable, str) or not pg_restore_executable.strip():
        raise RestorePreparationError(INVALID_PARAMETER, "Un parametro no es valido")
    if (
        isinstance(list_timeout_seconds, bool)
        or not isinstance(list_timeout_seconds, int)
        or list_timeout_seconds <= 0
    ):
        raise RestorePreparationError(INVALID_PARAMETER, "Un parametro no es valido")
    numeric_limits = (
        limits.max_entries,
        limits.max_package_bytes,
        limits.max_uncompressed_bytes,
        limits.max_compression_ratio,
        limits.stream_chunk_bytes,
    )
    if any(isinstance(value, bool) or value <= 0 for value in numeric_limits):
        raise RestorePreparationError(INVALID_PARAMETER, "Un limite no es valido")


def _validate_source_path(package_path: Path) -> None:
    if not package_path.exists():
        raise RestorePreparationError(PACKAGE_NOT_FOUND, "El paquete no existe")
    if not _regular_file(package_path):
        raise RestorePreparationError(
            PACKAGE_NOT_REGULAR_FILE,
            "El paquete no es un archivo regular",
        )


def _secure_output(path: Path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.chmod(path, 0o600, follow_symlinks=False)
        return os.fdopen(descriptor, "wb")
    except BaseException:
        os.close(descriptor)
        raise


def _copy_source_package(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str,
    chunk_size: int,
    max_bytes: int,
) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    digest = hashlib.sha256()
    copied = 0
    try:
        descriptor = os.open(source, flags)
        with os.fdopen(descriptor, "rb") as input_file, _secure_output(destination) as output:
            while chunk := input_file.read(chunk_size):
                copied += len(chunk)
                if copied > max_bytes:
                    raise RestorePreparationError(
                        PACKAGE_VALIDATION_FAILED,
                        "El paquete excede el limite permitido",
                    )
                digest.update(chunk)
                output.write(chunk)
    except RestorePreparationError:
        raise
    except OSError:
        raise RestorePreparationError(
            PACKAGE_VALIDATION_FAILED,
            "No fue posible copiar el paquete",
        ) from None
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise RestorePreparationError(
            PACKAGE_SHA256_MISMATCH,
            "El SHA-256 del paquete no coincide",
        )
    return actual_sha256


def _validate_package(package_path: Path, *, limits: PackageValidationLimits) -> dict:
    result = validate_backup_package(package_path, limits=limits)
    if not result.valid or result.manifest is None:
        code = UNAUTHORIZED_SCOPE if result.error_code == "INCOMPATIBLE_SCOPE" else PACKAGE_VALIDATION_FAILED
        raise RestorePreparationError(code, "El paquete no supero la validacion")
    manifest = result.manifest
    if manifest.get("scope") != _EXPECTED_SCOPE:
        raise RestorePreparationError(
            UNAUTHORIZED_SCOPE,
            "El alcance del paquete no esta autorizado",
        )
    return manifest


def _resolve_temp_root(temp_root: Path) -> Path:
    root = Path(temp_root)
    try:
        if root.is_symlink() or not root.is_dir():
            raise RestorePreparationError(
                TEMP_ROOT_INVALID,
                "El directorio temporal autorizado no es valido",
            )
        return root.resolve(strict=True)
    except RestorePreparationError:
        raise
    except OSError:
        raise RestorePreparationError(
            TEMP_ROOT_INVALID,
            "El directorio temporal autorizado no es accesible",
        ) from None


def _create_work_dir(temp_root: Path) -> Path:
    try:
        candidate = Path(tempfile.mkdtemp(prefix="restore-", dir=temp_root))
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise RestorePreparationError(
            MATERIALIZATION_FAILED,
            "No fue posible crear el directorio temporal",
        ) from None
    if not resolved.is_relative_to(temp_root):
        raise RestorePreparationError(
            TEMP_PATH_ESCAPE,
            "El directorio temporal quedo fuera de la raiz autorizada",
        )
    return resolved


def _copy_entry(
    archive: zipfile.ZipFile,
    *,
    internal_name: str,
    destination: Path,
    chunk_size: int,
    max_bytes: int,
) -> None:
    info = archive.getinfo(internal_name)
    if info.file_size > max_bytes:
        raise RestorePreparationError(MATERIALIZATION_FAILED, "Un artefacto excede el limite permitido")
    written = 0
    try:
        with archive.open(info, "r") as source, _secure_output(destination) as target:
            while chunk := source.read(chunk_size):
                written += len(chunk)
                if written > info.file_size or written > max_bytes:
                    raise RestorePreparationError(
                        MATERIALIZATION_FAILED,
                        "El artefacto excede el tamano declarado",
                    )
                target.write(chunk)
    except RestorePreparationError:
        raise
    except (KeyError, OSError, RuntimeError, NotImplementedError, EOFError, zipfile.BadZipFile):
        raise RestorePreparationError(
            MATERIALIZATION_FAILED,
            "No fue posible materializar los artefactos",
        ) from None
    if written != info.file_size:
        raise RestorePreparationError(
            MATERIALIZATION_FAILED,
            "El artefacto materializado tiene un tamano inconsistente",
        )


def _materialize_payload(
    package_path: Path,
    *,
    work_dir: Path,
    limits: PackageValidationLimits,
) -> tuple[Path, Path]:
    dump_path = work_dir / _LOCAL_DUMP_NAME
    restore_list_path = work_dir / _LOCAL_RESTORE_LIST_NAME
    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            _copy_entry(archive, internal_name=DATABASE_DUMP_PATH, destination=dump_path,
                        chunk_size=limits.stream_chunk_bytes, max_bytes=limits.max_uncompressed_bytes)
            _copy_entry(archive, internal_name=RESTORE_LIST_PATH, destination=restore_list_path,
                        chunk_size=limits.stream_chunk_bytes, max_bytes=limits.max_uncompressed_bytes)
    except RestorePreparationError:
        raise
    except (KeyError, OSError, RuntimeError, NotImplementedError, EOFError, zipfile.BadZipFile):
        raise RestorePreparationError(
            MATERIALIZATION_FAILED,
            "No fue posible abrir el paquete validado",
        ) from None
    return dump_path, restore_list_path


def _run_pg_restore_list(executable: str, dump_path: Path, *, timeout_seconds: int) -> str:
    try:
        completed = subprocess.run(
            [executable, "--list", str(dump_path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise RestorePreparationError(
            PG_RESTORE_LIST_FAILED,
            "No fue posible inspeccionar el dump",
        ) from None
    if completed.returncode != 0:
        raise RestorePreparationError(
            PG_RESTORE_LIST_FAILED,
            "pg_restore no pudo inspeccionar el dump",
        ) from None
    return completed.stdout or ""


def _semantic_toc_entries(toc: str) -> tuple[str, ...]:
    return tuple(line.rstrip() for line in toc.splitlines() if line.rstrip() and not line.lstrip().startswith(";"))


def _validate_and_compare_toc(actual_toc: str, packaged_toc: str, *, inventory: DatabaseInventory) -> tuple[str, ...]:
    try:
        validate_restore_toc(actual_toc, inventory)
        validate_restore_toc(packaged_toc, inventory)
    except BackupGenerationError:
        raise RestorePreparationError(
            TOC_VALIDATION_FAILED,
            "El TOC contiene objetos no autorizados",
        ) from None
    actual_entries = _semantic_toc_entries(actual_toc)
    packaged_entries = _semantic_toc_entries(packaged_toc)
    if actual_entries != packaged_entries:
        raise RestorePreparationError(TOC_MISMATCH, "El TOC real no coincide con restore.list")
    return actual_entries


def _cleanup_work_dir(work_dir: Path, authorized_root: Path) -> None:
    try:
        if not work_dir.exists() and not work_dir.is_symlink():
            return
        if work_dir.is_symlink():
            raise OSError("unsafe cleanup target")
        resolved = work_dir.resolve(strict=True)
        if not resolved.is_relative_to(authorized_root) or resolved == authorized_root:
            raise OSError("unsafe cleanup target")
        shutil.rmtree(resolved)
    except OSError:
        raise RestorePreparationError(
            CLEANUP_FAILED,
            "No fue posible limpiar los artefactos temporales",
        ) from None


@contextmanager
def prepare_restore_package(
    *, package_path: Path, expected_sha256: str, temp_root: Path,
    pg_restore_executable: str, inventory: DatabaseInventory,
    limits: PackageValidationLimits, list_timeout_seconds: int = 120,
) -> Iterator[PreparedRestore]:
    """Prepara artefactos que solo son validos dentro del bloque ``with``."""
    _validate_parameters(expected_sha256, pg_restore_executable, list_timeout_seconds, limits)
    source = Path(package_path)
    _validate_source_path(source)
    authorized_root = _resolve_temp_root(Path(temp_root))
    work_dir: Path | None = None
    primary_error: BaseException | None = None
    try:
        work_dir = _create_work_dir(authorized_root)
        private_package = work_dir / _LOCAL_PACKAGE_NAME
        verified_sha256 = _copy_source_package(
            source, private_package, expected_sha256=expected_sha256,
            chunk_size=limits.stream_chunk_bytes, max_bytes=limits.max_package_bytes,
        )
        manifest = _validate_package(private_package, limits=limits)
        dump_path, restore_list_path = _materialize_payload(
            private_package, work_dir=work_dir, limits=limits,
        )
        try:
            packaged_toc = restore_list_path.read_text(encoding="utf-8")
            private_package.unlink()
        except (OSError, UnicodeDecodeError):
            raise RestorePreparationError(MATERIALIZATION_FAILED, "restore.list no es legible") from None
        actual_toc = _run_pg_restore_list(
            pg_restore_executable, dump_path, timeout_seconds=list_timeout_seconds,
        )
        toc_entries = _validate_and_compare_toc(actual_toc, packaged_toc, inventory=inventory)
        yield PreparedRestore(
            work_dir=work_dir, database_dump_path=dump_path,
            restore_list_path=restore_list_path, manifest=manifest,
            package_sha256=verified_sha256, toc_entries=toc_entries,
        )
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        if work_dir is not None:
            try:
                _cleanup_work_dir(work_dir, authorized_root)
            except RestorePreparationError:
                if primary_error is None:
                    raise
                _LOGGER.error("Fallo sanitizado durante cleanup de staging")


__all__ = [
    "CLEANUP_FAILED", "INVALID_EXPECTED_SHA256", "INVALID_PARAMETER",
    "MATERIALIZATION_FAILED", "PACKAGE_NOT_FOUND", "PACKAGE_NOT_REGULAR_FILE",
    "PACKAGE_SHA256_MISMATCH", "PACKAGE_VALIDATION_FAILED",
    "PG_RESTORE_LIST_FAILED", "TEMP_PATH_ESCAPE", "TEMP_ROOT_INVALID",
    "TOC_MISMATCH", "TOC_VALIDATION_FAILED", "UNAUTHORIZED_SCOPE",
    "PreparedRestore", "RestorePreparationError", "prepare_restore_package",
]
