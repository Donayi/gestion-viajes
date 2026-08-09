"""Orquestacion de ejecuciones manuales y automaticas de respaldos."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.crud_respaldos import has_automatic_backup_in_period
from app.db.database import SessionLocal, engine
from app.services.backup_service import BackupGenerationResult, generate_logical_backup


BACKUP_DISABLED = "BACKUP_DISABLED"
BACKUP_ALREADY_RUNNING = "BACKUP_ALREADY_RUNNING"
_BACKUP_ADVISORY_LOCK_KEY = 0x444146524551424B
_LOGGER = logging.getLogger(__name__)


class BackupRuntimeError(Exception):
    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message[:500]


@contextmanager
def _generation_lock(database_engine: Engine) -> Iterator[None]:
    connection = database_engine.connect()
    locked = False
    try:
        locked = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": _BACKUP_ADVISORY_LOCK_KEY},
            ).scalar_one()
        )
        if not locked:
            raise BackupRuntimeError(
                BACKUP_ALREADY_RUNNING,
                "Ya existe una generacion de respaldo en curso",
            )
        yield
    finally:
        if locked:
            try:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": _BACKUP_ADVISORY_LOCK_KEY},
                )
            except Exception:
                _LOGGER.error("No fue posible liberar el bloqueo de respaldo")
        connection.close()


def run_backup(
    db: Session,
    *,
    trigger: str,
    application_version: str,
    actor_source: str,
    actor_original_id: str | None = None,
    actor_username_snapshot: str | None = None,
    actor_role_snapshot: str | None = None,
    actor_nombre_snapshot: str | None = None,
    database_engine: Engine = engine,
    config: Any = settings,
) -> BackupGenerationResult:
    if not config.backup_enabled:
        raise BackupRuntimeError(BACKUP_DISABLED, "El modulo de respaldos no esta habilitado")
    with _generation_lock(database_engine):
        return generate_logical_backup(
            db,
            trigger=trigger,
            application_version=application_version,
            actor_source=actor_source,
            actor_original_id=actor_original_id,
            actor_username_snapshot=actor_username_snapshot,
            actor_role_snapshot=actor_role_snapshot,
            actor_nombre_snapshot=actor_nombre_snapshot,
            database_engine=database_engine,
            config=config,
        )


def automatic_period(now: datetime, *, timezone_name: str) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(timezone_name)
    local_now = now.astimezone(timezone)
    start = datetime.combine(local_now.date(), time.min, tzinfo=timezone)
    return start, start + timedelta(days=1)


def run_due_automatic_backup(
    *,
    now: datetime | None = None,
    database_engine: Engine = engine,
    config: Any = settings,
    session_factory: Any = SessionLocal,
) -> bool:
    if not config.backup_enabled or not config.backup_daily_enabled:
        return False
    timezone = ZoneInfo(config.backup_timezone)
    current = (now or datetime.now(timezone)).astimezone(timezone)
    scheduled = time.fromisoformat(config.backup_daily_time)
    if current.time().replace(tzinfo=None) < scheduled:
        return False
    period_start, period_end = automatic_period(current, timezone_name=config.backup_timezone)
    db = session_factory()
    try:
        with _generation_lock(database_engine):
            if has_automatic_backup_in_period(db, start=period_start, end=period_end):
                return False
            generate_logical_backup(
                db,
                trigger="AUTOMATICO",
                application_version=config.app_version,
                actor_source="SYSTEM",
                database_engine=database_engine,
                config=config,
            )
            return True
    finally:
        db.close()


class DailyBackupScheduler:
    """Planificador diario en proceso con catch-up persistente tras reinicios."""

    def __init__(self, *, config: Any = settings) -> None:
        self._config = config
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self._config.backup_enabled or not self._config.backup_daily_enabled:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="dafreq-daily-backup",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                run_due_automatic_backup(config=self._config)
            except BackupRuntimeError as exc:
                if exc.code != BACKUP_ALREADY_RUNNING:
                    _LOGGER.error("Ejecucion automatica rechazada: %s", exc.code)
            except Exception:
                _LOGGER.error("Fallo interno sanitizado del respaldo automatico")
            self._stop_event.wait(60)


__all__ = [
    "BACKUP_ALREADY_RUNNING",
    "BACKUP_DISABLED",
    "BackupRuntimeError",
    "DailyBackupScheduler",
    "automatic_period",
    "run_backup",
    "run_due_automatic_backup",
]
