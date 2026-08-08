import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://logistica:change-me@db:5432/logistica_db",
)
os.environ.setdefault("SECRET_KEY", "change-me")


def _database_target(url: URL) -> tuple[str, str, str, int, str]:
    backend, separator, driver = url.drivername.partition("+")
    return (
        backend.casefold(),
        driver.casefold() if separator else "",
        (url.host or "").casefold(),
        url.port or 5432,
        url.database or "",
    )


def _validated_test_database_url() -> URL:
    raw_test_url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not raw_test_url:
        raise RuntimeError(
            "TEST_DATABASE_URL es obligatoria para pruebas con persistencia"
        )

    test_url = make_url(raw_test_url)
    development_url = make_url(os.environ["DATABASE_URL"])

    if _database_target(test_url) == _database_target(development_url):
        raise RuntimeError("TEST_DATABASE_URL no puede coincidir con DATABASE_URL")

    if not test_url.drivername.startswith("postgresql"):
        raise RuntimeError("TEST_DATABASE_URL debe usar PostgreSQL")

    if test_url.database != "logistica_test":
        raise RuntimeError(
            "TEST_DATABASE_URL debe apuntar exclusivamente a la base logistica_test"
        )

    if test_url.username != "logistica_test_user":
        raise RuntimeError(
            "TEST_DATABASE_URL debe usar exclusivamente el usuario logistica_test_user"
        )

    if test_url.host != "db_test":
        raise RuntimeError(
            "TEST_DATABASE_URL debe usar exclusivamente el host aislado db_test"
        )

    return test_url


@pytest.fixture
def app():
    from app.main import create_app

    app = create_app()
    app.router.on_startup.clear()
    return app


@pytest.fixture(scope="session")
def persistent_test_engine():
    test_url = _validated_test_database_url()
    engine = create_engine(test_url, future=True)
    try:
        from app.db.base import Base
        import app.models.models  # noqa: F401 - registra el metadata ORM completo

        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS control_respaldo")

        Base.metadata.create_all(bind=engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(persistent_test_engine):
    connection = persistent_test_engine.connect()
    transaction = None
    session = None
    try:
        transaction = connection.begin()
        session = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        yield session
    finally:
        try:
            if session is not None:
                session.close()
        finally:
            try:
                if transaction is not None and transaction.is_active:
                    transaction.rollback()
            finally:
                connection.close()

