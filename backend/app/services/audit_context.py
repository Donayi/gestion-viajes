import hashlib
import hmac
import ipaddress
import re
from collections.abc import Iterable, Mapping
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.audit_context import (
    AUDIT_CONTEXT_STATE_KEY,
    AuditContext,
    AuditContextState,
)
from app.schemas.bitacora import (
    ActorBitacora,
    TipoActorBitacora,
    sanitize_user_agent,
)


MAX_XFF_BYTES = 4096
MAX_XFF_HOPS = 32
UNRESOLVED_ROUTE = "RUTA_NO_RESUELTA"
IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def _parse_ip(value: str | None) -> IPAddress | None:
    # Ports, scoped IPv6 and whitespace are not part of the canonical address.
    if not isinstance(value, str) or not value or "%" in value:
        return None
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def trusted_proxy_networks(proxies: Iterable[str]) -> tuple[IPNetwork, ...]:
    return tuple(ipaddress.ip_network(proxy, strict=False) for proxy in proxies)


def _is_trusted(address: IPAddress, networks: tuple[IPNetwork, ...]) -> bool:
    return any(address.version == network.version and address in network for network in networks)


def resolve_audit_ip(
    peer: str | None,
    forwarded_values: Iterable[bytes],
    networks: tuple[IPNetwork, ...],
) -> IPAddress | None:
    """Use the available peer; production must certify upstream scope rewriting.

    Only XFF from an explicitly trusted peer is considered. Duplicate headers,
    invalid addresses and oversized chains fall back to that peer. If all hops
    are trusted, retain the peer rather than inventing a client identity.
    """
    peer_ip = _parse_ip(peer)
    if peer_ip is None or not _is_trusted(peer_ip, networks):
        return peer_ip
    values = []
    for value in forwarded_values:
        values.append(value)
        if len(values) > 1:
            return peer_ip
    if not values or len(values[0]) > MAX_XFF_BYTES:
        return peer_ip
    try:
        parts = values[0].decode("ascii").split(",")
    except UnicodeDecodeError:
        return peer_ip
    if len(parts) > MAX_XFF_HOPS:
        return peer_ip
    chain = [_parse_ip(part.strip(" \t")) for part in parts]
    if any(address is None for address in chain):
        return peer_ip
    for address in reversed(chain):
        if not _is_trusted(address, networks):
            return address
    return peer_ip


def _valid_hmac_key(key: str) -> bool:
    return bool(key.strip()) and len(key.encode("utf-8")) >= 32


def hash_audit_ip(address: IPAddress, key: str, version: int) -> str:
    if not 1 <= version <= 32767 or not _valid_hmac_key(key):
        raise ValueError("Configuración HMAC inválida")
    # Canonical v1 format (UTF-8): dafreq:audit-ip:v{version}:{ipaddress.compressed}
    # IPv4-mapped IPv6 stays IPv6. Never change this format without a version bump.
    message = f"dafreq:audit-ip:v{version}:{address.compressed}".encode("utf-8")
    return hmac.new(key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _http_method(value: str) -> str | None:
    return value if re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,10}", value) else None


def build_http_audit_context(
    *,
    config: Settings,
    method: str,
    peer: str | None,
    forwarded_values: Iterable[bytes] = (),
    user_agent: str | None = None,
    networks: tuple[IPNetwork, ...] | None = None,
) -> AuditContextState:
    ip_hash = None
    ip_version = None
    safe_agent = None
    if config.audit_enabled:
        safe_agent = sanitize_user_agent(user_agent, max_length=config.audit_user_agent_max_length)
        key = config.audit_ip_hmac_key.get_secret_value() if config.audit_ip_hmac_key else ""
        if _valid_hmac_key(key):
            address = resolve_audit_ip(
                peer,
                forwarded_values,
                networks if networks is not None else trusted_proxy_networks(config.audit_trusted_proxies),
            )
            if address is not None:
                ip_hash = hash_audit_ip(address, key, config.audit_ip_hash_version)
                ip_version = config.audit_ip_hash_version
    return AuditContextState(
        enabled=config.audit_enabled,
        context=AuditContext(
            request_id=uuid4(),
            actor=ActorBitacora(tipo=TipoActorBitacora.ANONIMO),
            ip_hash=ip_hash,
            ip_hash_version=ip_version,
            user_agent=safe_agent,
            metodo_http=_http_method(method),
            ruta_http=UNRESOLVED_ROUTE,
        ),
    )


def get_audit_state(scope: Mapping) -> AuditContextState | None:
    state = scope.get("state", {}).get(AUDIT_CONTEXT_STATE_KEY)
    return state if isinstance(state, AuditContextState) else None


def refresh_audit_route(scope: Mapping, state: AuditContextState) -> None:
    # Only a router-owned template: never scope['path'], raw_path or query_string.
    template = getattr(scope.get("route"), "path", None)
    if (
        not isinstance(template, str)
        or not template.startswith("/")
        or len(template) > 255
        or "?" in template
        or any(ord(character) < 32 or ord(character) == 127 for character in template)
    ):
        template = UNRESOLVED_ROUTE
    if state.context.ruta_http != template:
        state.context.ruta_http = template


def bind_authenticated_actor(
    state: AuditContextState | None,
    *,
    usuario_id: int,
    username: str,
    nombre: str,
    rol: str,
) -> None:
    if state is None or not state.enabled:
        return
    try:
        actor = ActorBitacora(
            tipo=TipoActorBitacora.USUARIO,
            usuario_id=usuario_id,
            username_snapshot=username,
            nombre_snapshot=nombre,
            rol_snapshot=rol,
        )
    except ValidationError:
        # Inconsistent legacy identity must not change functional authentication.
        return
    state.context.actor = actor


def build_system_audit_context(correlation_id: UUID | None = None) -> AuditContext:
    """Call once per operation, then reuse the returned correlation/context."""
    return AuditContext(
        correlation_id=correlation_id if correlation_id is not None else uuid4(),
        actor=ActorBitacora(tipo=TipoActorBitacora.SISTEMA),
    )
