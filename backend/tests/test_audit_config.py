import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


DATABASE_URL = "postgresql+psycopg://test:test@db/test"
PRODUCTION_SECRET = "production-secret-key-with-at-least-32-chars"


def make_settings(**overrides) -> Settings:
    values = {
        "database_url": DATABASE_URL,
        "app_env": "development",
        "environment": None,
        "secret_key": "change-me-in-production",
        "audit_enabled": False,
        "audit_ip_hmac_key": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_audit_configuration_defaults_are_safe():
    config = make_settings()

    assert config.audit_enabled is False
    assert config.audit_ip_hmac_key is None
    assert config.audit_ip_hash_version == 1
    assert config.audit_trusted_proxies == []
    assert config.audit_user_agent_max_length == 300
    assert config.audit_retention_months == 24
    assert config.audit_max_json_bytes == 8192


def test_audit_can_be_enabled_without_key_outside_production():
    assert make_settings(audit_enabled=True).audit_ip_hmac_key is None


def test_disabled_audit_does_not_require_hmac_key_in_production():
    config = make_settings(
        app_env="production",
        secret_key=PRODUCTION_SECRET,
        audit_enabled=False,
    )

    assert config.audit_ip_hmac_key is None


@pytest.mark.parametrize("value", [None, "", "   ", "short-key"])
def test_enabled_audit_rejects_missing_empty_or_short_key_in_production(value):
    with pytest.raises(ValidationError, match="AUDIT_IP_HMAC_KEY"):
        make_settings(
            app_env="production",
            secret_key=PRODUCTION_SECRET,
            audit_enabled=True,
            audit_ip_hmac_key=value,
        )


def test_audit_hmac_minimum_is_measured_in_utf8_bytes():
    config = make_settings(
        app_env="production",
        secret_key=PRODUCTION_SECRET,
        audit_enabled=True,
        audit_ip_hmac_key="á" * 16,
    )

    assert isinstance(config.audit_ip_hmac_key, SecretStr)
    assert config.audit_ip_hmac_key.get_secret_value() == "á" * 16


@pytest.mark.parametrize(
    ("value", "accepted"),
    [
        ("a" * 31, False),
        ("a" * 32, True),
        ("a" * 33, True),
        ("á" * 16, True),
    ],
)
def test_audit_hmac_enforces_exact_utf8_byte_boundary(value, accepted):
    kwargs = {
        "app_env": "production",
        "secret_key": PRODUCTION_SECRET,
        "audit_enabled": True,
        "audit_ip_hmac_key": value,
    }
    if accepted:
        assert make_settings(**kwargs).audit_ip_hmac_key.get_secret_value() == value
    else:
        with pytest.raises(ValidationError, match="AUDIT_IP_HMAC_KEY"):
            make_settings(**kwargs)


def test_environment_also_enables_production_audit_validation():
    with pytest.raises(ValidationError, match="AUDIT_IP_HMAC_KEY"):
        make_settings(
            app_env="development",
            environment="production",
            secret_key=PRODUCTION_SECRET,
            audit_enabled=True,
        )


@pytest.mark.parametrize(
    ("app_env", "environment", "expected"),
    [
        ("production", "development", True),
        ("development", "production", True),
        ("production", "production", True),
        ("development", "test", False),
    ],
)
def test_production_detection_uses_either_existing_indicator(
    app_env, environment, expected
):
    config = make_settings(
        app_env=app_env,
        environment=environment,
        secret_key=PRODUCTION_SECRET,
    )
    assert config.is_production_environment() is expected


def test_empty_audit_hmac_key_is_normalized_to_absence():
    assert make_settings(audit_ip_hmac_key="  ").audit_ip_hmac_key is None


@pytest.mark.parametrize(
    "field_name",
    [
        "audit_ip_hash_version",
        "audit_user_agent_max_length",
        "audit_retention_months",
        "audit_max_json_bytes",
    ],
)
def test_positive_audit_configuration_values_are_required(field_name):
    with pytest.raises(ValidationError):
        make_settings(**{field_name: 0})


@pytest.mark.parametrize("value", [1, 8192])
def test_audit_json_limit_accepts_approved_bounds(value):
    assert make_settings(audit_max_json_bytes=value).audit_max_json_bytes == value


@pytest.mark.parametrize("value", [0, 8193])
def test_audit_json_limit_rejects_values_outside_approved_bounds(value):
    with pytest.raises(ValidationError):
        make_settings(audit_max_json_bytes=value)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        ("127.0.0.1, 10.0.0.9", ["127.0.0.1", "10.0.0.9"]),
        ('["127.0.0.1", "2001:db8::1"]', ["127.0.0.1", "2001:db8::1"]),
        (["10.0.0.7/24", "2001:db8::/32"], ["10.0.0.0/24", "2001:db8::/32"]),
        ("127.0.0.1,127.0.0.1", ["127.0.0.1"]),
    ],
)
def test_trusted_proxies_accept_and_normalize_supported_formats(raw, expected):
    assert make_settings(audit_trusted_proxies=raw).audit_trusted_proxies == expected


@pytest.mark.parametrize("raw", ["proxy.example.com", "10.0.0.1/99", "127.0.0.1,"])
def test_trusted_proxies_reject_invalid_values(raw):
    with pytest.raises(ValidationError, match="AUDIT_TRUSTED_PROXIES"):
        make_settings(audit_trusted_proxies=raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('["127.0.0.1", "10.0.0.7/24"]', ["127.0.0.1", "10.0.0.0/24"]),
        ("127.0.0.1, 2001:db8::1", ["127.0.0.1", "2001:db8::1"]),
        ("", []),
    ],
)
def test_trusted_proxies_are_loaded_from_real_environment(monkeypatch, raw, expected):
    monkeypatch.setenv("AUDIT_TRUSTED_PROXIES", raw)

    assert make_settings().audit_trusted_proxies == expected


def test_invalid_trusted_proxies_from_environment_are_rejected(monkeypatch):
    monkeypatch.setenv("AUDIT_TRUSTED_PROXIES", "proxy.example.com")

    with pytest.raises(ValidationError, match="AUDIT_TRUSTED_PROXIES"):
        make_settings()


def test_existing_production_secret_validation_is_preserved():
    with pytest.raises(ValidationError, match="SECRET_KEY insegura para producción"):
        make_settings(app_env="production", secret_key="change-me-in-production")
