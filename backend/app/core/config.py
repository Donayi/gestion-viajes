from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestión de Viajes API"
    app_env: str = "development"
    environment: str | None = None
    database_url: str
    strict_evidence_validation: bool = False
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

    @staticmethod
    def _normalize_environment(value: str | None) -> str:
        return (value or "").strip().lower()

    def is_production_environment(self) -> bool:
        return "production" in {
            self._normalize_environment(self.app_env),
            self._normalize_environment(self.environment),
        }

    def validate_runtime_config(self) -> "Settings":
        if not self.is_production_environment():
            return self

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

        return self

    @model_validator(mode="after")
    def validate_runtime_config_model(self) -> "Settings":
        return self.validate_runtime_config()

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
