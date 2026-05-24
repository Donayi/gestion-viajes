from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestión de Viajes API"
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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
