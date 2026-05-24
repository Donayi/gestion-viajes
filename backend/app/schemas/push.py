from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    user_agent: str | None = None


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class PushSubscriptionResponse(BaseModel):
    id_subscription: int
    id_usuario: int
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    failure_count: int

    model_config = ConfigDict(from_attributes=True)


class PushStatusResponse(BaseModel):
    enabled: bool
    vapid_public_key_configured: bool
    has_active_subscriptions: bool
    active_subscriptions_count: int


class PushTestResponse(BaseModel):
    enviado: bool
    mensaje: str
    total_subscriptions: int = 0
    success_count: int = 0
    failure_count: int = 0
    errores_resumidos: list[str] = []
