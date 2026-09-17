from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.schemas.audit_context import AUDIT_CONTEXT_STATE_KEY
from app.services.audit_context import (
    build_http_audit_context,
    refresh_audit_route,
    trusted_proxy_networks,
)


class AuditContextMiddleware:
    """Prepare scope-local context only; no persistence or request body reads."""

    def __init__(self, app: ASGIApp, config: Settings) -> None:
        self.app = app
        self.config = config
        self.networks = trusted_proxy_networks(config.audit_trusted_proxies)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        agent = None
        forwarded = ()
        peer = None
        if self.config.audit_enabled:
            client = scope.get("client")
            peer = client[0] if client else None
            # Examine only the two approved headers; never keep a header mapping.
            agent_values = [
                value for name, value in scope.get("headers", ()) if name.lower() == b"user-agent"
            ]
            if len(agent_values) == 1:
                agent = agent_values[0].decode("latin-1")
            forwarded = (
                value for name, value in scope.get("headers", ()) if name.lower() == b"x-forwarded-for"
            )
        state = build_http_audit_context(
            config=self.config,
            method=scope.get("method", ""),
            peer=peer,
            forwarded_values=forwarded,
            user_agent=agent,
            networks=self.networks,
        )
        scope.setdefault("state", {})[AUDIT_CONTEXT_STATE_KEY] = state

        async def send_with_context(message: Message) -> None:
            if message["type"] == "http.response.start":
                refresh_audit_route(scope, state)
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            # Holder remains in this scope for outer exception handlers; no global state.
            refresh_audit_route(scope, state)
