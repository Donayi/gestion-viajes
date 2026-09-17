from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.bitacora import ActorBitacora, TipoActorBitacora


class AuditContext(BaseModel):
    """Shared safe fields only: no request, headers, ORM objects or configuration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    request_id: UUID | None = Field(default=None, frozen=True)
    correlation_id: UUID | None = None
    actor: ActorBitacora
    ip_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    ip_hash_version: int | None = Field(default=None, ge=1, le=32767)
    user_agent: str | None = Field(default=None, max_length=300)
    metodo_http: str | None = Field(default=None, max_length=10)
    ruta_http: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_context(self) -> "AuditContext":
        if self.request_id is None and self.correlation_id is None:
            raise ValueError("El contexto requiere request_id o correlation_id")
        if (self.ip_hash is None) != (self.ip_hash_version is None):
            raise ValueError("ip_hash e ip_hash_version deben coexistir")
        if self.request_id is None and any(
            value is not None
            for value in (self.metodo_http, self.ruta_http, self.ip_hash, self.user_agent)
        ):
            raise ValueError("El contexto no HTTP no admite datos del request")
        if self.actor.tipo is TipoActorBitacora.SISTEMA and self.request_id is not None:
            raise ValueError("El contexto SISTEMA no admite request_id")
        return self


@dataclass
class AuditContextState:
    """One holder per scope; sync dependencies share it across threadpool calls."""

    enabled: bool
    context: AuditContext


AUDIT_CONTEXT_STATE_KEY = "audit_context"
