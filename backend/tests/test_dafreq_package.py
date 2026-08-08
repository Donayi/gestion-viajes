import hashlib
import json
import stat
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.services.backup_package import (
    CHECKSUMS_PATH,
    CHECKSUM_MISMATCH,
    COMPRESSION_RATIO_EXCEEDED,
    DATABASE_DUMP_PATH,
    DUPLICATE_ENTRY,
    INVALID_MANIFEST,
    INVALID_ZIP,
    MANIFEST_PATH,
    MISSING_ENTRY,
    PACKAGE_ENTRIES,
    RESTORE_LIST_PATH,
    SYMLINK_ENTRY,
    TOO_MANY_ENTRIES,
    UNCOMPRESSED_SIZE_EXCEEDED,
    UNEXPECTED_ENTRY,
    UNSAFE_PATH,
    UNSUPPORTED_DUMP_FORMAT,
    UNSUPPORTED_FORMAT_VERSION,
    UNSUPPORTED_POSTGRES_VERSION,
    BackupPackageBuildError,
    PackageValidationLimits,
    create_backup_package,
    generate_backup_filename,
    read_backup_manifest,
    sha256_file,
    validate_backup_package,
)
from app.services.backup_package import _compression_ratio


LIMITS = PackageValidationLimits(
    max_entries=16,
    max_package_bytes=10 * 1024 * 1024,
    max_uncompressed_bytes=10 * 1024 * 1024,
    max_compression_ratio=100.0,
    stream_chunk_bytes=128,
)


@pytest.fixture
def valid_package(tmp_path: Path) -> Path:
    dump = tmp_path / "source.dump"
    restore_list = tmp_path / "source.list"
    dump.write_bytes(b"PGDMP\x01 dummy custom dump")
    restore_list.write_text("TABLE public.viajes\n", encoding="utf-8")
    return create_backup_package(
        database_dump=dump,
        restore_list=restore_list,
        destination_dir=tmp_path,
        backup_id=uuid4(),
        created_at=datetime(2026, 8, 8, 12, 30, 45, tzinfo=timezone.utc),
        trigger="MANUAL",
        application_name="Gestion de Viajes",
        application_version="1.0.0",
        dump_tool_version="pg_dump 16.4",
        tables=[{"schema": "public", "name": "viajes", "row_count": 3}],
        limits=LIMITS,
    )


def _rewrite_package(
    source: Path,
    destination: Path,
    *,
    remove: str | None = None,
    add: tuple[str, bytes] | None = None,
    mutate: dict[str, bytes] | None = None,
    duplicate: str | None = None,
    symlink: str | None = None,
) -> Path:
    mutate = mutate or {}
    with zipfile.ZipFile(source, "r") as original:
        contents = [(info.filename, original.read(info)) for info in original.infolist()]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in contents:
                if name != remove:
                    archive.writestr(name, mutate.get(name, content))
            if add:
                archive.writestr(*add)
            if duplicate:
                archive.writestr(duplicate, dict(contents)[duplicate])
            if symlink:
                info = zipfile.ZipInfo(symlink)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, b"manifest.json")
    return destination


def _mutated_manifest(package: Path, mutator) -> bytes:
    with zipfile.ZipFile(package, "r") as archive:
        manifest = json.loads(archive.read(MANIFEST_PATH))
    mutator(manifest)
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()


def _rewrite_with_manifest(source: Path, destination: Path, content: bytes) -> Path:
    with zipfile.ZipFile(source, "r") as archive:
        checksums = json.loads(archive.read(CHECKSUMS_PATH))
    checksums[MANIFEST_PATH] = hashlib.sha256(content).hexdigest()
    checksum_content = json.dumps(
        checksums, sort_keys=True, separators=(",", ":")
    ).encode()
    return _rewrite_package(
        source,
        destination,
        mutate={MANIFEST_PATH: content, CHECKSUMS_PATH: checksum_content},
    )


def test_generate_backup_filename_is_portable():
    backup_id = UUID("12345678-1234-5678-9abc-123456789abc")
    created_at = datetime(2026, 8, 8, 10, 11, 12, tzinfo=timezone.utc)

    name = generate_backup_filename(created_at=created_at, backup_id=backup_id)

    assert name == "dafreq-backup-20260808T101112+0000-12345678-1234-5678-9abc-123456789abc.dafreq-backup"


def test_create_valid_package_with_dummy_files(valid_package):
    assert valid_package.is_file()
    assert validate_backup_package(valid_package, limits=LIMITS).valid is True
    with zipfile.ZipFile(valid_package) as archive:
        assert set(archive.namelist()) == PACKAGE_ENTRIES


def test_read_manifest(valid_package):
    manifest = read_backup_manifest(valid_package, limits=LIMITS)

    assert manifest["format"] == "dafreq-backup"
    assert manifest["totals"]["package_size_bytes"] == valid_package.stat().st_size
    assert manifest["integrity"] == {
        "payload_files": [DATABASE_DUMP_PATH, RESTORE_LIST_PATH],
        "manifest_covered_by": CHECKSUMS_PATH,
        "checksums_self_hash": False,
        "package_hash": "external",
    }
    assert {item["path"] for item in manifest["files"]} == {
        DATABASE_DUMP_PATH,
        RESTORE_LIST_PATH,
    }


def test_internal_checksums_are_correct(valid_package):
    with zipfile.ZipFile(valid_package) as archive:
        sums = json.loads(archive.read(CHECKSUMS_PATH))
        assert set(sums) == {DATABASE_DUMP_PATH, RESTORE_LIST_PATH, MANIFEST_PATH}
        assert CHECKSUMS_PATH not in sums
        for name, expected in sums.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected


def test_rejects_corrupt_zip(tmp_path):
    package = tmp_path / "corrupt.dafreq-backup"
    package.write_bytes(b"not-a-zip")

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == INVALID_ZIP


def test_rejects_missing_file(valid_package, tmp_path):
    package = _rewrite_package(valid_package, tmp_path / "missing.zip", remove=RESTORE_LIST_PATH)

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == MISSING_ENTRY


def test_rejects_additional_file(valid_package, tmp_path):
    package = _rewrite_package(valid_package, tmp_path / "additional.zip", add=("extra.txt", b"x"))

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == UNEXPECTED_ENTRY


def test_rejects_tampered_checksum(valid_package, tmp_path):
    package = _rewrite_package(
        valid_package,
        tmp_path / "tampered.zip",
        mutate={DATABASE_DUMP_PATH: b"tampered"},
    )

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == CHECKSUM_MISMATCH


@pytest.mark.parametrize(
    ("field", "value"),
    [("format_version", 2)],
)
def test_rejects_unknown_format_version(valid_package, tmp_path, field, value):
    content = _mutated_manifest(valid_package, lambda manifest: manifest.__setitem__(field, value))
    package = _rewrite_with_manifest(valid_package, tmp_path / "version.zip", content)

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == UNSUPPORTED_FORMAT_VERSION


def test_rejects_incompatible_postgresql_major(valid_package, tmp_path):
    content = _mutated_manifest(
        valid_package, lambda manifest: manifest["database"].__setitem__("server_major", 15)
    )
    package = _rewrite_with_manifest(valid_package, tmp_path / "major.zip", content)

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == UNSUPPORTED_POSTGRES_VERSION


def test_rejects_incompatible_dump_format(valid_package, tmp_path):
    content = _mutated_manifest(
        valid_package, lambda manifest: manifest["database"].__setitem__("dump_format", "plain")
    )
    package = _rewrite_with_manifest(valid_package, tmp_path / "format.zip", content)

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == UNSUPPORTED_DUMP_FORMAT


@pytest.mark.parametrize(
    "mutator",
    [
        lambda manifest: manifest.__setitem__("trigger", []),
        lambda manifest: manifest["files"][0].__setitem__("path", []),
    ],
    ids=["trigger-list", "payload-path-list"],
)
def test_rejects_non_hashable_manifest_values(valid_package, tmp_path, mutator):
    content = _mutated_manifest(valid_package, mutator)
    package = _rewrite_with_manifest(
        valid_package,
        tmp_path / f"invalid-types-{uuid4()}.zip",
        content,
    )

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == INVALID_MANIFEST


def test_create_package_does_not_overwrite_existing_destination(tmp_path):
    dump = tmp_path / "source.dump"
    restore_list = tmp_path / "source.list"
    dump.write_bytes(b"PGDMP dummy")
    restore_list.write_text("TABLE public.viajes\n", encoding="utf-8")
    backup_id = UUID("12345678-1234-5678-9abc-123456789abc")
    created_at = datetime(2026, 8, 8, 10, 11, 12, tzinfo=timezone.utc)
    destination = tmp_path / generate_backup_filename(
        created_at=created_at,
        backup_id=backup_id,
    )
    original_content = b"preexisting-package"
    destination.write_bytes(original_content)

    with pytest.raises(BackupPackageBuildError):
        create_backup_package(
            database_dump=dump,
            restore_list=restore_list,
            destination_dir=tmp_path,
            backup_id=backup_id,
            created_at=created_at,
            trigger="MANUAL",
            application_name="Gestion de Viajes",
            application_version="1.0.0",
            dump_tool_version="pg_dump 16.4",
            tables=[],
            limits=LIMITS,
        )

    assert destination.read_bytes() == original_content


def test_rejects_traversal(valid_package, tmp_path):
    package = _rewrite_package(valid_package, tmp_path / "traversal.zip", add=("../evil", b"x"))

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == UNSAFE_PATH


@pytest.mark.parametrize("name", ["/absolute", "C:/absolute"])
def test_rejects_absolute_path(valid_package, tmp_path, name):
    package = _rewrite_package(valid_package, tmp_path / f"absolute-{uuid4()}.zip", add=(name, b"x"))

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == UNSAFE_PATH


def test_rejects_duplicate_entry(valid_package, tmp_path):
    package = _rewrite_package(
        valid_package, tmp_path / "duplicate.zip", duplicate=MANIFEST_PATH
    )

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == DUPLICATE_ENTRY


def test_rejects_symlink(valid_package, tmp_path):
    package = _rewrite_package(valid_package, tmp_path / "symlink.zip", symlink="link")

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is False
    assert result.error_code == SYMLINK_ENTRY


def test_rejects_too_many_entries(valid_package):
    limits = PackageValidationLimits(3, 10_000_000, 10_000_000, 100.0)

    result = validate_backup_package(valid_package, limits=limits)
    assert result.valid is False
    assert result.error_code == TOO_MANY_ENTRIES


def test_rejects_expanded_size(valid_package):
    limits = PackageValidationLimits(16, 10_000_000, 1, 100.0)

    result = validate_backup_package(valid_package, limits=limits)
    assert result.valid is False
    assert result.error_code == UNCOMPRESSED_SIZE_EXCEEDED


def test_rejects_excessive_compression_ratio(tmp_path):
    package = tmp_path / "compression-bomb.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_PATH, b"{}")
        archive.writestr(DATABASE_DUMP_PATH, b"A" * (1024 * 1024))
        archive.writestr(RESTORE_LIST_PATH, b"TABLE public.viajes\n")
        archive.writestr(CHECKSUMS_PATH, b"{}")
    with zipfile.ZipFile(package, "r") as archive:
        entries = archive.infolist()
        uncompressed_size = sum(entry.file_size for entry in entries)
        compressed_size = sum(entry.compress_size for entry in entries)

    assert compressed_size > 0
    actual_ratio = uncompressed_size / compressed_size
    limit = actual_ratio - 0.01
    assert actual_ratio > limit > 1
    limits = PackageValidationLimits(16, 10_000_000, 10_000_000, limit)

    result = validate_backup_package(package, limits=limits)
    assert result.valid is False
    assert result.error_code == COMPRESSION_RATIO_EXCEEDED


def test_empty_payload_files_do_not_cause_division_by_zero(tmp_path):
    dump = tmp_path / "empty.dump"
    restore_list = tmp_path / "empty.list"
    dump.write_bytes(b"")
    restore_list.write_bytes(b"")
    package = create_backup_package(
        database_dump=dump,
        restore_list=restore_list,
        destination_dir=tmp_path,
        backup_id=uuid4(),
        created_at=datetime(2026, 8, 8, 12, 30, 45, tzinfo=timezone.utc),
        trigger="MANUAL",
        application_name="Gestion de Viajes",
        application_version="1.0.0",
        dump_tool_version="pg_dump 16.4",
        tables=[],
        limits=LIMITS,
    )

    result = validate_backup_package(package, limits=LIMITS)
    assert result.valid is True
    assert result.error_code is None


def test_nonempty_entry_with_zero_compressed_size_has_infinite_ratio():
    entries = [SimpleNamespace(file_size=1, compress_size=0)]

    assert _compression_ratio(entries) == float("inf")


def test_fully_empty_entries_have_zero_compression_ratio():
    entries = [SimpleNamespace(file_size=0, compress_size=0)]

    assert _compression_ratio(entries) == 0.0


def test_implementation_does_not_use_extractall():
    source = Path(__file__).parents[1] / "app" / "services" / "backup_package.py"

    assert ".extractall(" not in source.read_text(encoding="utf-8")


def test_package_sha256_is_stable(valid_package):
    first = validate_backup_package(valid_package, limits=LIMITS)
    second = validate_backup_package(valid_package, limits=LIMITS)

    assert first.valid is True
    assert first.package_sha256 == second.package_sha256 == sha256_file(valid_package)
