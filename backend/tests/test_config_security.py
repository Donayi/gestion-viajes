import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_allows_default_secret_key_in_development():
    settings = Settings(
        database_url="postgresql+psycopg://logistica:change-me@db:5432/logistica_db",
        app_env="development",
        secret_key="change-me-in-production",
    )

    assert settings.secret_key == "change-me-in-production"
    assert settings.is_production_environment() is False


def test_settings_allows_default_secret_key_in_test():
    settings = Settings(
        database_url="postgresql+psycopg://logistica:change-me@db:5432/logistica_db",
        environment="test",
        secret_key="change-me-in-production",
    )

    assert settings.is_production_environment() is False


@pytest.mark.parametrize(
    ("field_name", "secret_key"),
    [
        ("app_env", ""),
        ("app_env", "change-me-in-production"),
        ("app_env", "short-secret-key"),
        ("environment", ""),
        ("environment", "change-me-in-production"),
        ("environment", "short-secret-key"),
    ],
)
def test_settings_rejects_weak_secret_key_in_production(field_name, secret_key):
    payload = {
        "database_url": "postgresql+psycopg://logistica:change-me@db:5432/logistica_db",
        "secret_key": secret_key,
        field_name: "production",
    }

    with pytest.raises(ValidationError, match="SECRET_KEY insegura para producción"):
        Settings(**payload)


def test_settings_allows_strong_secret_key_in_production():
    settings = Settings(
        database_url="postgresql+psycopg://logistica:change-me@db:5432/logistica_db",
        app_env="production",
        secret_key="super-secret-production-key-with-32-chars!",
    )

    assert settings.is_production_environment() is True
