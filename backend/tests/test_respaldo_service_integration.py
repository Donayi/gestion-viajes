"""Integracion real de la generacion logica de respaldos con PostgreSQL 16."""

from __future__ import annotations

import re
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import delete

from app.core.config import settings
from app.models.models import RespaldoControl
from app.services import backup_service
from app.services.backup_package import (
    DATABASE_DUMP_PATH,
    RESTORE_LIST_PATH,
    sha256_file,
    validate_backup_package,
)


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _integration_config(tmp_path: Path, database_url: str) -> SimpleNamespace:
    return SimpleNamespace(
        app_name=settings.app_name,
        database_url=database_url,
        backup_temp_dir=tmp_path / "work",
        backup_storage_dir=tmp_path / "storage",
        backup_max_package_entries=settings.backup_max_package_entries,
        backup_max_upload_bytes=settings.backup_max_upload_bytes,
        backup_max_uncompressed_bytes=settings.backup_max_uncompressed_bytes,
        backup_max_compression_ratio=settings.backup_max_compression_ratio,
        backup_stream_chunk_bytes=settings.backup_stream_chunk_bytes,
    )


def test_generate_logical_backup_against_postgresql_16(
    db_session,
    persistent_test_engine,
    tmp_path,
):
    test_url = persistent_test_engine.url
    assert test_url.database == "logistica_test"
    assert test_url.username == "logistica_test_user"
    assert test_url.host == "db_test"

    config = _integration_config(
        tmp_path,
        test_url.render_as_string(hide_password=False),
    )
    result = None
    try:
        result = backup_service.generate_logical_backup(
            db_session,
            trigger="MANUAL",
            application_version="integration-test",
            database_engine=persistent_test_engine,
            config=config,
        )

        package_path = result.package_path
        assert package_path.exists()
        assert package_path.parent == tmp_path / "storage"
        assert package_path.suffix == ".dafreq-backup"
        assert _SHA256_PATTERN.fullmatch(result.package_sha256)
        assert result.package_sha256 == sha256_file(package_path)

        manifest = result.manifest
        assert manifest["format"] == "dafreq-backup"
        assert manifest["database"]["server_major"] == 16
        assert manifest["database"]["dump_format"] == "custom"
        assert manifest["scope"]["backup_control_tables"] is False
        assert manifest["scope"]["r2_objects"] is False
        assert manifest["scope"]["r2_metadata"] is True
        assert all(table["schema"] == "public" for table in manifest["tables"])

        validation = validate_backup_package(
            package_path,
            limits=backup_service._package_limits(config),
        )
        assert validation.valid is True
        assert validation.manifest == manifest
        assert validation.package_sha256 == result.package_sha256

        with persistent_test_engine.connect() as connection:
            inventory = backup_service._load_inventory(connection)
            actual_counts = backup_service.count_public_tables(connection, inventory)
        expected_counts = {
            (item["schema"], item["name"]): item["row_count"]
            for item in actual_counts
        }
        manifest_counts = {
            (item["schema"], item["name"]): item["row_count"]
            for item in manifest["tables"]
        }
        assert manifest_counts == expected_counts
        assert manifest["totals"]["rows"] == sum(expected_counts.values())

        extracted_dump = tmp_path / "database.dump"
        with zipfile.ZipFile(package_path, "r") as archive:
            assert RESTORE_LIST_PATH in archive.namelist()
            restore_list = archive.read(RESTORE_LIST_PATH).decode("utf-8")
            with archive.open(DATABASE_DUMP_PATH, "r") as source:
                extracted_dump.write_bytes(source.read())

        _, pg_restore = backup_service.validate_postgresql_tools()
        listed = subprocess.run(
            [pg_restore.executable, "--list", str(extracted_dump)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert listed.returncode == 0
        assert "control_respaldo" not in listed.stdout.casefold()
        assert "control_respaldo" not in restore_list.casefold()
        assert backup_service.validate_restore_toc(listed.stdout, inventory)
        assert backup_service.validate_restore_toc(restore_list, inventory)

        persisted = db_session.get(RespaldoControl, result.backup_id)
        assert persisted is not None
        assert persisted.estado == "DISPONIBLE"
        assert persisted.sha256 == sha256_file(package_path)
        assert persisted.size_bytes == package_path.stat().st_size
        assert persisted.table_count == len(manifest["tables"])
        assert persisted.row_count == manifest["totals"]["rows"]
        assert persisted.postgres_version.startswith("16.")
    finally:
        if result is not None:
            db_session.execute(
                delete(RespaldoControl).where(
                    RespaldoControl.id_respaldo == result.backup_id
                )
            )
            db_session.commit()
