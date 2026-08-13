from datetime import time
import ipaddress
import json
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestión de Viajes API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    environment: str | None = None
    database_url: str
    strict_evidence_validation: bool = False
    bootstrap_admin_enabled: bool = False
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    r2_region: str = "auto"
    r2_endpoint_url: str | None = None
    r2_public_base_url: str | None = None
    r2_presign_expiration_seconds: int = 900
    telegram_enabled: bool = False
    telegram_bot_token: str | None = None
    telegram_default_chat_id: str | None = None
    app_public_url: str | None = None
    web_push_enabled: bool = False
    web_push_vapid_public_key: str | None = None
    web_push_vapid_private_key: str | None = None
    web_push_subject: str = "mailto:admin@dafreqlogistica.com"
    audit_enabled: bool = False
    audit_ip_hmac_key: SecretStr | None = None
    audit_ip_hash_version: int = Field(default=1, gt=0)
    audit_trusted_proxies: Annotated[list[str], NoDecode] = Field(default_factory=list)
    audit_user_agent_max_length: int = Field(default=300, gt=0)
    audit_retention_months: int = Field(default=24, gt=0)
    audit_max_json_bytes: int = Field(default=8192, gt=0, le=8192)
    backup_enabled: bool = True
    backup_storage_dir: Path = Path("/var/lib/dafreq-backups")
    backup_temp_dir: Path = Path("/var/lib/dafreq-backups/work")
    backup_max_upload_bytes: int = Field(default=2 * 1024**3, gt=0)
    backup_max_uncompressed_bytes: int = Field(default=8 * 1024**3, gt=0)
    backup_max_compression_ratio: float = Field(default=100.0, gt=1)
    backup_daily_enabled: bool = True
    backup_daily_time: str = "02:00"
    backup_timezone: str = "America/Mexico_City"
    backup_retention_automatic_count: int = Field(default=30, ge=0)
    backup_retention_pre_restore_count: int = Field(default=10, ge=0)
    backup_validation_ttl_minutes: int = Field(default=60, gt=0)
    backup_confirmation_ttl_minutes: int = Field(default=5, gt=0)
    backup_operation_timeout_seconds: int = Field(default=3600, gt=0)
    backup_drain_timeout_seconds: int = Field(default=30, gt=0)
    backup_worker_poll_seconds: int = Field(default=2, gt=0)
    backup_temp_retention_hours: int = Field(default=24, gt=0)
    backup_max_package_entries: int = Field(default=16, gt=0)
    backup_stream_chunk_bytes: int = Field(default=1024 * 1024, gt=0)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        if isinstance(value, list):
            return [item.strip() for item in value if item and item.strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ]
            if stripped.startswith("["):
                import json

                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    @field_validator("audit_ip_hmac_key", mode="before")
    @classmethod
    def normalize_audit_ip_hmac_key(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("audit_trusted_proxies", mode="before")
    @classmethod
    def parse_audit_trusted_proxies(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return []
            if normalized.startswith("["):
                parsed = json.loads(normalized)
                if not isinstance(parsed, list):
                    raise ValueError("AUDIT_TRUSTED_PROXIES debe ser una lista")
                values = parsed
            else:
                values = normalized.split(",")
        elif isinstance(value, list):
            values = value
        else:
            raise ValueError("AUDIT_TRUSTED_PROXIES debe ser una lista")

        proxies: list[str] = []
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    "AUDIT_TRUSTED_PROXIES solo acepta direcciones IP o redes CIDR"
                )
            candidate = item.strip()
            try:
                if "/" in candidate:
                    proxy = str(ipaddress.ip_network(candidate, strict=False))
                else:
                    proxy = str(ipaddress.ip_address(candidate))
            except ValueError as exc:
                raise ValueError(
                    "AUDIT_TRUSTED_PROXIES solo acepta direcciones IP o redes CIDR"
                ) from exc
            if proxy not in proxies:
                proxies.append(proxy)
        return proxies

    @field_validator("backup_storage_dir", "backup_temp_dir", mode="before")
    @classmethod
    def validate_backup_directory(cls, value: str | Path) -> Path:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("Los directorios de respaldo no pueden estar vacíos")
        return Path(normalized)

    @field_validator("backup_daily_time")
    @classmethod
    def validate_backup_daily_time(cls, value: str) -> str:
        normalized = value.strip()
        try:
            parsed = time.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("BACKUP_DAILY_TIME debe usar el formato HH:MM") from exc
        if len(normalized) != 5 or parsed.second or parsed.microsecond:
            raise ValueError("BACKUP_DAILY_TIME debe usar el formato HH:MM")
        return normalized

    @field_validator("backup_timezone")
    @classmethod
    def validate_backup_timezone(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("BACKUP_TIMEZONE no puede estar vacía")
        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("BACKUP_TIMEZONE debe ser una zona horaria IANA válida") from exc
        return normalized

    @staticmethod
    def _normalize_environment(value: str | None) -> str:
        return (value or "").strip().lower()

    def is_production_environment(self) -> bool:
        return "production" in {
            self._normalize_environment(self.app_env),
            self._normalize_environment(self.environment),
        }

    def validate_runtime_config(self) -> "Settings":
        if self.is_production_environment():
            normalized_secret = (self.secret_key or "").strip()
            if (
                not normalized_secret
                or normalized_secret == "change-me-in-production"
                or len(normalized_secret) < 32
            ):
                raise ValueError(
                    "SECRET_KEY insegura para producción. Configura una clave no vacía, "
                    "distinta al valor por defecto y de al menos 32 caracteres."
                )

            if self.audit_enabled:
                audit_key = (
                    self.audit_ip_hmac_key.get_secret_value()
                    if self.audit_ip_hmac_key is not None
                    else ""
                )
                if len(audit_key.encode("utf-8")) < 32:
                    raise ValueError(
                        "AUDIT_IP_HMAC_KEY es obligatoria cuando la auditoría está "
                        "activa en producción y debe tener al menos 32 bytes UTF-8."
                    )

        return self

    @model_validator(mode="after")
    def validate_runtime_config_model(self) -> "Settings":
        return self.validate_runtime_config()

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
