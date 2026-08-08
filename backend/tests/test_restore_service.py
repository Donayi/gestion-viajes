from __future__ import annotations

import os
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services import restore_service as service
from app.services import backup_package as package_service
from app.services.backup_package import (
    INCOMPATIBLE_SCOPE,
    PackageValidationLimits,
    PackageValidationResult,
    create_backup_package,
    sha256_file,
)
from app.services.backup_service import DatabaseInventory


LIMITS = PackageValidationLimits(
    max_entries=16,
    max_package_bytes=10_000_000,
    max_uncompressed_bytes=10_000_000,
    max_compression_ratio=100.0,
    stream_chunk_bytes=32,
)

VALID_TOC = "\n".join(
    [
        "; Archive created at a variable time",
        "4; 2615 2200 SCHEMA - public owner",
        "3848; 0 0 COMMENT - SCHEMA public pg_database_owner",
        "1; 1259 1 TABLE public viajes owner",
        "2; 0 1 TABLE DATA public viajes owner",
        "3; 1259 2 SEQUENCE public viajes_id_seq owner",
        "4; 0 0 SEQUENCE OWNED BY public viajes_id_seq owner",
        "5; 0 0 SEQUENCE SET public viajes_id_seq owner",
        "6; 2604 3 DEFAULT public viajes id owner",
        "7; 1259 4 INDEX public ix_viajes owner",
        "8; 2606 5 CONSTRAINT public viajes viajes_pkey owner",
        "9; 2606 6 FK CONSTRAINT public viajes viajes_cliente_fkey owner",
    ]
) + "\n"


def _inventory() -> DatabaseInventory:
    return DatabaseInventory(
        tables=frozenset({"viajes"}),
        sequences=frozenset({"viajes_id_seq"}),
        indexes=frozenset({"ix_viajes"}),
        constraints=frozenset(
            {("viajes", "viajes_pkey"), ("viajes", "viajes_cliente_fkey")}
        ),
    )


def _package(tmp_path: Path, *, dump: bytes = b"PGDMP dummy payload") -> Path:
    dump_path = tmp_path / "source.dump"
    list_path = tmp_path / "source.list"
    destination = tmp_path / "packages"
    destination.mkdir()
    dump_path.write_bytes(dump)
    list_path.write_text(VALID_TOC, encoding="utf-8")
    return create_backup_package(
        database_dump=dump_path,
        restore_list=list_path,
        destination_dir=destination,
        backup_id=UUID("12345678-1234-5678-9abc-123456789abc"),
        created_at=datetime(
            2026,
            8,
            8,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        trigger="MANUAL",
        application_name="Gestion de Viajes",
        application_version="test",
        dump_tool_version="16.14",
        tables=[{"schema": "public", "name": "viajes", "row_count": 0}],
        limits=LIMITS,
    )


@pytest.fixture
def valid_package(tmp_path, monkeypatch):
    package = _package(tmp_path)
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=VALID_TOC,
            stderr="",
        ),
    )
    return package


def _prepare(package: Path, temp_root: Path, **overrides):
    values = {
        "package_path": package,
        "expected_sha256": sha256_file(package),
        "temp_root": temp_root,
        "pg_restore_executable": "/tools/pg_restore",
        "inventory": _inventory(),
        "limits": LIMITS,
    }
    values.update(overrides)
    return service.prepare_restore_package(**values)


def test_rejects_missing_package(tmp_path):
    with pytest.raises(service.RestorePreparationError) as captured:
        with service.prepare_restore_package(
            package_path=tmp_path / "missing.dafreq-backup",
            expected_sha256="a" * 64,
            temp_root=tmp_path,
            pg_restore_executable="pg_restore",
            inventory=_inventory(),
            limits=LIMITS,
        ):
            pass
    assert captured.value.code == service.PACKAGE_NOT_FOUND


def test_rejects_non_regular_package(tmp_path):
    directory = tmp_path / "package.dafreq-backup"
    directory.mkdir()
    with pytest.raises(service.RestorePreparationError) as captured:
        with service.prepare_restore_package(
            package_path=directory,
            expected_sha256="a" * 64,
            temp_root=tmp_path,
            pg_restore_executable="pg_restore",
            inventory=_inventory(),
            limits=LIMITS,
        ):
            pass
    assert captured.value.code == service.PACKAGE_NOT_REGULAR_FILE


def test_rejects_sha256_mismatch(valid_package, tmp_path):
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path, expected_sha256="0" * 64):
            pass
    assert captured.value.code == service.PACKAGE_SHA256_MISMATCH


def test_rejects_structurally_invalid_package(tmp_path):
    package = tmp_path / "invalid.dafreq-backup"
    package.write_bytes(b"not a zip")
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(package, tmp_path):
            pass
    assert captured.value.code == service.PACKAGE_VALIDATION_FAILED


def test_rejects_unauthorized_scope(valid_package, tmp_path, monkeypatch):
    monkeypatch.setattr(
        service,
        "validate_backup_package",
        lambda *args, **kwargs: PackageValidationResult(
            valid=False,
            backup_id=None,
            format_version=None,
            manifest=None,
            package_size_bytes=valid_package.stat().st_size,
            package_sha256=sha256_file(valid_package),
            error_code=INCOMPATIBLE_SCOPE,
        ),
    )
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.UNAUTHORIZED_SCOPE


def test_materializes_only_fixed_payload_names(valid_package, tmp_path):
    with _prepare(valid_package, tmp_path) as prepared:
        assert prepared.work_dir.parent == tmp_path.resolve()
        assert prepared.database_dump_path.name == "database.dump"
        assert prepared.restore_list_path.name == "restore.list"
        assert {item.name for item in prepared.work_dir.iterdir()} == {
            "database.dump",
            "restore.list",
        }
        assert prepared.package_sha256 == sha256_file(valid_package)
        assert prepared.manifest["scope"]["backup_control_tables"] is False


def test_materialization_reads_in_configured_blocks(tmp_path, monkeypatch):
    package = _package(tmp_path, dump=b"x" * 512)
    manifest = service._validate_package(package, limits=LIMITS)
    monkeypatch.setattr(service, "_validate_package", lambda *args, **kwargs: manifest)
    requested_sizes = []
    original_read = service.zipfile.ZipExtFile.read

    def recording_read(stream, size=-1):
        requested_sizes.append(size)
        return original_read(stream, size)

    monkeypatch.setattr(service.zipfile.ZipExtFile, "read", recording_read)
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=VALID_TOC, stderr=""),
    )
    with _prepare(package, tmp_path):
        pass
    assert requested_sizes.count(LIMITS.stream_chunk_bytes) > 2
    assert all(size <= LIMITS.stream_chunk_bytes for size in requested_sizes if size > 0)


def test_runtime_never_uses_extractall(valid_package, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("extractall must never be called")

    monkeypatch.setattr(service.zipfile.ZipFile, "extractall", forbidden)
    with _prepare(valid_package, tmp_path):
        pass


def test_rejects_work_directory_outside_authorized_root(
    valid_package,
    tmp_path,
    monkeypatch,
):
    outside = tmp_path.parent / "outside-restore-test"
    outside.mkdir(exist_ok=True)
    monkeypatch.setattr(service.tempfile, "mkdtemp", lambda **kwargs: str(outside))
    try:
        with pytest.raises(service.RestorePreparationError) as captured:
            with _prepare(valid_package, tmp_path):
                pass
        assert captured.value.code == service.TEMP_PATH_ESCAPE
    finally:
        outside.rmdir()


def test_pg_restore_list_invocation_is_exact_and_non_destructive(
    tmp_path,
    monkeypatch,
):
    package = _package(tmp_path)
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout=VALID_TOC, stderr="")

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    with _prepare(package, tmp_path) as prepared:
        expected_dump = str(prepared.database_dump_path)
    assert captured["args"] == ["/tools/pg_restore", "--list", expected_dump]
    assert "shell" not in captured["kwargs"]
    assert not any(
        option in captured["args"]
        for option in ("--clean", "--create", "--use-list", "--dbname")
    )


def test_accepts_valid_real_toc(valid_package, tmp_path):
    with _prepare(valid_package, tmp_path) as prepared:
        assert prepared.toc_entries[0] == "4; 2615 2200 SCHEMA - public owner"
        assert len(prepared.toc_entries) == 11


@pytest.mark.parametrize(
    "unexpected_line",
    [
        "1; 1259 1 TABLE private viajes owner",
        "1; 1259 1 TABLE control_respaldo respaldos owner",
    ],
)
def test_rejects_toc_outside_public(
    valid_package,
    tmp_path,
    monkeypatch,
    unexpected_line,
):
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=VALID_TOC + unexpected_line + "\n",
            stderr="",
        ),
    )
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.TOC_VALIDATION_FAILED


def test_rejects_semantic_toc_difference(valid_package, tmp_path, monkeypatch):
    changed = VALID_TOC.replace(
        "1; 1259 1 TABLE public viajes owner",
        "1; 1259 1 TABLE public viajes another_owner",
    )
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=changed, stderr=""),
    )
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.TOC_MISMATCH


def test_tolerates_only_approved_non_semantic_toc_differences(
    valid_package,
    tmp_path,
    monkeypatch,
):
    actual = (
        "; Different generated header\r\n\r\n"
        + "\r\n".join(line + "   " for line in VALID_TOC.splitlines() if not line.startswith(";"))
        + "\r\n"
    )
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=actual, stderr=""),
    )
    with _prepare(valid_package, tmp_path) as prepared:
        assert len(prepared.toc_entries) == 11


def test_cleans_staging_when_subprocess_fails(valid_package, tmp_path, monkeypatch):
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="fatal password=super-secret absolute=/private/path",
        ),
    )
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.PG_RESTORE_LIST_FAILED
    assert "super-secret" not in captured.value.public_message
    assert "/private/path" not in captured.value.public_message
    assert not list(tmp_path.glob("restore-*"))


def test_cleans_staging_after_successful_context(valid_package, tmp_path):
    with _prepare(valid_package, tmp_path) as prepared:
        work_dir = prepared.work_dir
        assert work_dir.exists()
    assert not work_dir.exists()


def test_cleans_staging_when_toc_comparison_fails(
    valid_package,
    tmp_path,
    monkeypatch,
):
    changed_order = "\n".join(reversed(VALID_TOC.splitlines())) + "\n"
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=changed_order,
            stderr="",
        ),
    )
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.TOC_MISMATCH
    assert not list(tmp_path.glob("restore-*"))


def test_subprocess_exception_is_sanitized(valid_package, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["pg_restore", "--list", "/private/secret.dump"],
            timeout=1,
            stderr="super-secret",
        )

    monkeypatch.setattr(service.subprocess, "run", fail)
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.PG_RESTORE_LIST_FAILED
    assert "super-secret" not in captured.value.public_message
    assert "/private" not in captured.value.public_message
    assert captured.value.__cause__ is None


def test_validator_streams_dump_without_using_small_entry_reader(tmp_path, monkeypatch):
    package = _package(tmp_path, dump=b"large-dump" * 10_000)
    names_read_into_memory = []
    original = package_service._read_entry

    def recording_reader(archive, info, *, chunk_size, max_bytes):
        names_read_into_memory.append(info.filename)
        return original(archive, info, chunk_size=chunk_size, max_bytes=max_bytes)

    monkeypatch.setattr(package_service, "_read_entry", recording_reader)
    result = package_service.validate_backup_package(package, limits=LIMITS)
    assert result.valid is True
    assert package_service.DATABASE_DUMP_PATH not in names_read_into_memory
    assert package_service.RESTORE_LIST_PATH not in names_read_into_memory
    assert set(names_read_into_memory) == {
        package_service.MANIFEST_PATH,
        package_service.CHECKSUMS_PATH,
    }


def test_source_change_after_private_copy_does_not_change_staging(
    tmp_path,
    monkeypatch,
):
    package = _package(tmp_path)
    original_copy = service._copy_source_package

    def copy_then_mutate(*args, **kwargs):
        result = original_copy(*args, **kwargs)
        package.write_bytes(b"replacement after private copy")
        return result

    monkeypatch.setattr(service, "_copy_source_package", copy_then_mutate)
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=VALID_TOC, stderr=""),
    )
    expected = sha256_file(package)
    with _prepare(package, tmp_path, expected_sha256=expected) as prepared:
        assert prepared.package_sha256 == expected
        assert prepared.database_dump_path.read_bytes() == b"PGDMP dummy payload"


def test_only_payload_remains_at_yield_and_files_are_private(valid_package, tmp_path):
    with _prepare(valid_package, tmp_path) as prepared:
        entries = list(prepared.work_dir.iterdir())
        assert {entry.name for entry in entries} == {"database.dump", "restore.list"}
        assert not (prepared.work_dir / service._LOCAL_PACKAGE_NAME).exists()
        for entry in entries:
            assert stat.S_IMODE(entry.stat().st_mode) == 0o600


def test_private_package_has_private_permissions(valid_package, tmp_path, monkeypatch):
    observed = {}
    original = service._validate_package

    def inspect_private_package(path, *, limits):
        observed["mode"] = stat.S_IMODE(path.stat().st_mode)
        return original(path, limits=limits)

    monkeypatch.setattr(service, "_validate_package", inspect_private_package)
    with _prepare(valid_package, tmp_path):
        pass
    assert observed["mode"] == 0o600


@pytest.mark.parametrize("invalid_hash", ["a" * 63, "g" * 64, "A" * 64, "", None])
def test_rejects_invalid_or_noncanonical_expected_sha(valid_package, tmp_path, invalid_hash):
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path, expected_sha256=invalid_hash):
            pass
    assert captured.value.code == service.INVALID_EXPECTED_SHA256


def test_expected_sha_contract_accepts_lowercase(valid_package, tmp_path):
    expected = sha256_file(valid_package)
    assert expected == expected.lower()
    with _prepare(valid_package, tmp_path, expected_sha256=expected):
        pass


@pytest.mark.parametrize("root_kind", ["missing", "file", "symlink"])
def test_rejects_invalid_temp_roots(valid_package, tmp_path, root_kind):
    root = tmp_path / root_kind
    if root_kind == "file":
        root.write_text("not a directory", encoding="utf-8")
    elif root_kind == "symlink":
        target = tmp_path / "target-root"
        target.mkdir()
        root.symlink_to(target, target_is_directory=True)
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, root):
            pass
    assert captured.value.code == service.TEMP_ROOT_INVALID


@pytest.mark.parametrize(
    "overrides",
    [
        {"pg_restore_executable": ""},
        {"pg_restore_executable": "   "},
        {"pg_restore_executable": None},
        {"list_timeout_seconds": 0},
        {"list_timeout_seconds": -1},
        {"list_timeout_seconds": 1.5},
        {"list_timeout_seconds": True},
    ],
)
def test_rejects_invalid_execution_parameters(valid_package, tmp_path, overrides):
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path, **overrides):
            pass
    assert captured.value.code == service.INVALID_PARAMETER


def test_second_payload_failure_cleans_partial_staging(valid_package, tmp_path, monkeypatch):
    original = service._copy_entry
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise service.RestorePreparationError(
                service.MATERIALIZATION_FAILED,
                "No fue posible materializar los artefactos",
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "_copy_entry", fail_second)
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.MATERIALIZATION_FAILED
    assert not list(tmp_path.glob("restore-*"))


def test_cleanup_failure_without_primary_error_is_observable(valid_package, tmp_path, monkeypatch):
    monkeypatch.setattr(service.shutil, "rmtree", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("secret path")))
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.CLEANUP_FAILED
    assert "secret" not in captured.value.public_message
    assert captured.value.__cause__ is None


def test_cleanup_failure_preserves_primary_error(valid_package, tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(
        service.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="super-secret"),
    )
    monkeypatch.setattr(service.shutil, "rmtree", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("private path")))
    with pytest.raises(service.RestorePreparationError) as captured:
        with _prepare(valid_package, tmp_path):
            pass
    assert captured.value.code == service.PG_RESTORE_LIST_FAILED
    assert "super-secret" not in captured.value.public_message
    assert "private path" not in caplog.text


def test_cleanup_never_removes_outside_authorized_root(valid_package, tmp_path, monkeypatch):
    outside = tmp_path.parent / "outside-cleanup-guard"
    outside.mkdir(exist_ok=True)
    removed = []
    monkeypatch.setattr(service.tempfile, "mkdtemp", lambda **kwargs: str(outside))
    monkeypatch.setattr(service.shutil, "rmtree", lambda path: removed.append(path))
    try:
        with pytest.raises(service.RestorePreparationError) as captured:
            with _prepare(valid_package, tmp_path):
                pass
        assert captured.value.code == service.TEMP_PATH_ESCAPE
        assert removed == []
        assert outside.exists()
    finally:
        outside.rmdir()
