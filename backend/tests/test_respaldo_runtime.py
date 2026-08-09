from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.crud.crud_respaldos import create_respaldo, has_automatic_backup_in_period
from app.services import backup_runtime as runtime


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeConnection:
    def __init__(self, locked=True):
        self.locked = locked
        self.commands = []
        self.closed = False

    def execute(self, statement, params):
        self.commands.append((str(statement), params))
        return ScalarResult(self.locked if len(self.commands) == 1 else True)

    def close(self):
        self.closed = True


class FakeEngine:
    def __init__(self, locked=True):
        self.connection = FakeConnection(locked)

    def connect(self):
        return self.connection


class FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _config(**overrides):
    values = {
        "backup_enabled": True,
        "backup_daily_enabled": True,
        "backup_daily_time": "02:00",
        "backup_timezone": "America/Mexico_City",
        "backup_worker_poll_seconds": 2,
        "app_version": "test",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_concurrent_generation_is_rejected_before_generator(monkeypatch):
    called = False

    def generator(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(runtime, "generate_logical_backup", generator)
    with pytest.raises(runtime.BackupRuntimeError) as captured:
        runtime.run_backup(
            FakeSession(),
            trigger="MANUAL",
            application_version="test",
            actor_source="USER",
            database_engine=FakeEngine(locked=False),
            config=_config(),
        )
    assert captured.value.code == runtime.BACKUP_ALREADY_RUNNING
    assert called is False


def test_automatic_backup_is_idempotent_for_local_day(monkeypatch):
    generated = False
    session = FakeSession()
    monkeypatch.setattr(runtime, "has_automatic_backup_in_period", lambda *args, **kwargs: True)
    monkeypatch.setattr(runtime, "generate_logical_backup", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    result = runtime.run_due_automatic_backup(
        now=datetime(2026, 8, 8, 14, tzinfo=UTC),
        database_engine=FakeEngine(),
        config=_config(),
        session_factory=lambda: session,
    )
    assert result is False
    assert session.closed is True
    assert generated is False


def test_automatic_backup_runs_once_after_scheduled_time(monkeypatch):
    captured = {}
    session = FakeSession()
    monkeypatch.setattr(runtime, "has_automatic_backup_in_period", lambda *args, **kwargs: False)
    monkeypatch.setattr(runtime, "generate_logical_backup", lambda db, **kwargs: captured.update(kwargs))
    result = runtime.run_due_automatic_backup(
        now=datetime(2026, 8, 8, 14, tzinfo=UTC),
        database_engine=FakeEngine(),
        config=_config(),
        session_factory=lambda: session,
    )
    assert result is True
    assert captured["trigger"] == "AUTOMATICO"
    assert captured["actor_source"] == "SYSTEM"


def test_automatic_backup_waits_until_configured_local_time(monkeypatch):
    monkeypatch.setattr(runtime, "has_automatic_backup_in_period", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    assert runtime.run_due_automatic_backup(
        now=datetime(2026, 8, 8, 6, tzinfo=UTC),
        database_engine=FakeEngine(),
        config=_config(),
        session_factory=FakeSession,
    ) is False


@pytest.mark.parametrize("value", ["2:00", "25:00", "02:00:00", "invalid"])
def test_invalid_daily_time_configuration_is_rejected(value):
    with pytest.raises(ValueError):
        Settings(database_url="postgresql+psycopg://test:test@db/test", backup_daily_time=value)


def test_valid_daily_time_and_timezone_configuration():
    config = Settings(
        database_url="postgresql+psycopg://test:test@db/test",
        backup_daily_time="02:00",
        backup_timezone="America/Mexico_City",
    )
    assert config.backup_daily_time == "02:00"
    assert config.backup_timezone == "America/Mexico_City"


def test_automatic_period_is_persistently_idempotent(db_session):
    created_at = datetime(2026, 8, 8, 8, tzinfo=UTC)
    create_respaldo(
        db_session,
        nombre_archivo="automatic-period.dafreq-backup",
        ruta_relativa="automatic-period.dafreq-backup",
        origen="AUTOMATICO",
        estado="FALLIDO",
        actor_source="SYSTEM",
        created_at=created_at,
    )
    assert has_automatic_backup_in_period(
        db_session,
        start=datetime(2026, 8, 8, tzinfo=UTC),
        end=datetime(2026, 8, 9, tzinfo=UTC),
    ) is True
