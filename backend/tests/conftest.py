import os
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://logistica:change-me@db:5432/logistica_db",
)
os.environ.setdefault("SECRET_KEY", "change-me")


@pytest.fixture
def app():
    from app.main import create_app

    app = create_app()
    app.router.on_startup.clear()
    return app

