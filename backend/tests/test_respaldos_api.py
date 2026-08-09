from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.deps import get_db


ADMIN = {"user_id": 1, "username": "AdminGeneral", "role": "ADMIN"}
OPERADOR = {"user_id": 2, "username": "OperadorUno", "role": "OPERADOR"}
BACKUP_ID = UUID("12345678-1234-5678-9abc-123456789abc")


class FakeDb:
    pass


def _record(**overrides):
    values = {
        "id_respaldo": BACKUP_ID,
        "nombre_archivo": f"dafreq-backup-20260808T120000+0000-{BACKUP_ID}.dafreq-backup",
        "ruta_relativa": f"dafreq-backup-20260808T120000+0000-{BACKUP_ID}.dafreq-backup",
        "origen": "MANUAL",
        "estado": "DISPONIBLE",
        "size_bytes": 10,
        "sha256": "a" * 64,
        "table_count": 5,
        "row_count": 12,
        "created_at": datetime(2026, 8, 8, 12, tzinfo=UTC),
        "started_at": datetime(2026, 8, 8, 12, tzinfo=UTC),
        "completed_at": datetime(2026, 8, 8, 12, 1, tzinfo=UTC),
        "error_detalle": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _headers(profile):
    token = create_access_token(
        {
            "sub": str(profile["user_id"]),
            "username": profile["username"],
            "role": profile["role"],
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _user(profile):
    return SimpleNamespace(
        id_usuario=profile["user_id"],
        username=profile["username"],
        nombre="Usuario",
        apellido="Prueba",
        activo=True,
        rol=SimpleNamespace(nombre=profile["role"]),
        operador=None,
    )


@pytest.fixture
def client(app, monkeypatch):
    from app.api import deps_auth

    app.dependency_overrides[get_db] = lambda: iter([FakeDb()])
    monkeypatch.setattr(
        deps_auth,
        "get_user_with_role_and_operador",
        lambda db, user_id: _user(ADMIN if user_id == 1 else OPERADOR),
    )
    with TestClient(app) as current:
        yield current
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/respaldos/manual"),
        ("get", "/respaldos"),
        ("get", f"/respaldos/{BACKUP_ID}/descarga"),
    ],
)
def test_backup_endpoints_require_authentication(client, method, path):
    kwargs = {"json": {}} if method == "post" else {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/respaldos/manual"),
        ("get", "/respaldos"),
        ("get", f"/respaldos/{BACKUP_ID}/descarga"),
    ],
)
def test_backup_endpoints_reject_non_admin(client, method, path):
    kwargs = {"headers": _headers(OPERADOR)}
    if method == "post":
        kwargs["json"] = {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403


def test_manual_generation_returns_persisted_result(client, monkeypatch):
    from app.api import routes_respaldos

    record = _record()
    captured = {}

    def fake_run(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(backup_id=BACKUP_ID)

    monkeypatch.setattr(routes_respaldos, "run_backup", fake_run)
    monkeypatch.setattr(routes_respaldos, "get_respaldo_by_id", lambda db, backup_id: record)
    response = client.post("/respaldos/manual", json={}, headers=_headers(ADMIN))
    assert response.status_code == 200
    assert response.json()["estado"] == "DISPONIBLE"
    assert captured["trigger"] == "MANUAL"
    assert captured["actor_source"] == "USER"
    assert captured["actor_username_snapshot"] == "AdminGeneral"


def test_history_is_admin_only_and_returns_sanitized_failure(client, monkeypatch):
    from app.api import routes_respaldos

    failed = _record(
        estado="FALLIDO",
        size_bytes=None,
        sha256=None,
        error_detalle="pg_dump no pudo generar el respaldo",
    )
    monkeypatch.setattr(routes_respaldos, "list_respaldos", lambda *args, **kwargs: ([failed], 1))
    response = client.get("/respaldos", headers=_headers(ADMIN))
    assert response.status_code == 200
    assert response.json()["items"][0]["error_mensaje"] == "pg_dump no pudo generar el respaldo"
    assert "DATABASE_URL" not in response.text


def test_download_returns_verified_registered_file(client, tmp_path, monkeypatch):
    from app.api import routes_respaldos

    payload = b"valid portable package"
    filename = _record().nombre_archivo
    package = tmp_path / filename
    package.write_bytes(payload)
    record = _record(
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    monkeypatch.setattr(routes_respaldos.settings, "backup_storage_dir", tmp_path)
    monkeypatch.setattr(routes_respaldos, "get_respaldo_by_id", lambda *args: record)
    response = client.get(f"/respaldos/{BACKUP_ID}/descarga", headers=_headers(ADMIN))
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["x-content-type-options"] == "nosniff"


def test_download_rejects_unknown_identifier(client, monkeypatch):
    from app.api import routes_respaldos

    monkeypatch.setattr(routes_respaldos, "get_respaldo_by_id", lambda *args: None)
    response = client.get(f"/respaldos/{BACKUP_ID}/descarga", headers=_headers(ADMIN))
    assert response.status_code == 404


@pytest.mark.parametrize("relative", ["../outside.dafreq-backup", "/tmp/outside.dafreq-backup"])
def test_download_rejects_path_outside_storage(client, tmp_path, monkeypatch, relative):
    from app.api import routes_respaldos

    record = _record(ruta_relativa=relative)
    monkeypatch.setattr(routes_respaldos.settings, "backup_storage_dir", tmp_path)
    monkeypatch.setattr(routes_respaldos, "get_respaldo_by_id", lambda *args: record)
    response = client.get(f"/respaldos/{BACKUP_ID}/descarga", headers=_headers(ADMIN))
    assert response.status_code == 409


def test_download_rejects_missing_file(client, tmp_path, monkeypatch):
    from app.api import routes_respaldos

    monkeypatch.setattr(routes_respaldos.settings, "backup_storage_dir", tmp_path)
    monkeypatch.setattr(routes_respaldos, "get_respaldo_by_id", lambda *args: _record())
    response = client.get(f"/respaldos/{BACKUP_ID}/descarga", headers=_headers(ADMIN))
    assert response.status_code == 404


def test_download_rejects_unsafe_persisted_filename(client, tmp_path, monkeypatch):
    from app.api import routes_respaldos

    record = _record(nombre_archivo='unsafe".dafreq-backup', ruta_relativa='unsafe".dafreq-backup')
    monkeypatch.setattr(routes_respaldos.settings, "backup_storage_dir", tmp_path)
    monkeypatch.setattr(routes_respaldos, "get_respaldo_by_id", lambda *args: record)
    response = client.get(f"/respaldos/{BACKUP_ID}/descarga", headers=_headers(ADMIN))
    assert response.status_code == 409
