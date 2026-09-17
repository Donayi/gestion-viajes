import hashlib
import hmac
import ipaddress
import re
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.schemas.audit_context import AuditContext
from app.schemas.bitacora import (
    ActorBitacora,
    BitacoraEventoCreateInternal,
    TipoActorBitacora,
)
from app.services.audit_context import (
    MAX_XFF_BYTES,
    MAX_XFF_HOPS,
    UNRESOLVED_ROUTE,
    bind_authenticated_actor,
    build_http_audit_context,
    build_system_audit_context,
    hash_audit_ip,
    refresh_audit_route,
    resolve_audit_ip,
    trusted_proxy_networks,
)


KEY = "audit-test-key-not-for-production-123456"


def configuration(**overrides):
    values = dict(
        database_url="postgresql+psycopg://test:test@invalid/test",
        app_env="test",
        environment=None,
        audit_enabled=True,
        audit_ip_hmac_key=KEY,
        audit_ip_hash_version=1,
        audit_trusted_proxies=[],
        audit_user_agent_max_length=300,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("address", ["192.0.2.7", "2001:db8::7"])
def test_hmac_canonical_message_and_digest(address):
    parsed = ipaddress.ip_address(address)
    digest = hash_audit_ip(parsed, KEY, 1)
    expected = hmac.new(
        KEY.encode("utf-8"),
        f"dafreq:audit-ip:v1:{parsed.compressed}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert digest == expected
    assert hash_audit_ip(parsed, KEY, 1) == digest
    assert hash_audit_ip(parsed, "another-test-key-at-least-32-bytes-long", 1) != digest
    assert hash_audit_ip(parsed, KEY, 2) != digest
    assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_equivalent_ipv6_addresses_have_same_hash():
    compact = ipaddress.ip_address("2001:db8::7")
    expanded = ipaddress.ip_address("2001:0db8:0000:0000:0000:0000:0000:0007")
    assert hash_audit_ip(compact, KEY, 1) == hash_audit_ip(expanded, KEY, 1)
    assert hash_audit_ip(ipaddress.ip_address("::ffff:192.0.2.7"), KEY, 1) != hash_audit_ip(
        ipaddress.ip_address("192.0.2.7"), KEY, 1
    )


@pytest.mark.parametrize("key,version", [("short", 1), (" " * 32, 1), (KEY, 0), (KEY, 32768)])
def test_hmac_rejects_invalid_configuration(key, version):
    with pytest.raises(ValueError):
        hash_audit_ip(ipaddress.ip_address("192.0.2.7"), key, version)


@pytest.mark.parametrize(
    "peer,headers,proxies,expected",
    [
        ("192.0.2.7", [b"198.51.100.8"], [], "192.0.2.7"),
        ("10.0.0.2", [b"192.0.2.7"], ["10.0.0.2"], "192.0.2.7"),
        ("10.0.0.2", [b"192.0.2.7, 10.0.0.3"], ["10.0.0.0/24"], "192.0.2.7"),
        # The forged leftmost prefix cannot replace the first untrusted hop.
        ("10.0.0.2", [b"203.0.113.99, 192.0.2.7"], ["10.0.0.0/24"], "192.0.2.7"),
        ("2001:db8:1::2", [b"2001:db8:2::7, 2001:db8:1::3"], ["2001:db8:1::/64"], "2001:db8:2::7"),
        ("10.0.0.2", [], ["10.0.0.2"], "10.0.0.2"),
        ("10.0.0.2", [b"10.0.0.3"], ["10.0.0.0/24"], "10.0.0.2"),
        (None, [b"192.0.2.7"], ["10.0.0.0/24"], None),
        ("unknown", [b"192.0.2.7"], ["10.0.0.0/24"], None),
        ("fe80::1%eth0", [], [], None),
    ],
)
def test_proxy_resolution(peer, headers, proxies, expected):
    result = resolve_audit_ip(peer, headers, trusted_proxy_networks(proxies))
    assert (str(result) if result is not None else None) == expected


@pytest.mark.parametrize(
    "headers",
    [
        [b"invalid, 192.0.2.7"],
        [b"192.0.2.7,"],
        [b""],
        [b"192.0.2.7:80"],
        [b"[2001:db8::7]"],
        [b"192.0.2.7\r\n"],
        [b"\xff"],
        [b"192.0.2.7", b"198.51.100.8"],
        [b"1" * (MAX_XFF_BYTES + 1)],
        [b", ".join([b"192.0.2.7"] * (MAX_XFF_HOPS + 1))],
    ],
)
def test_unsafe_xff_falls_back_to_valid_peer(headers):
    assert resolve_audit_ip("10.0.0.2", headers, trusted_proxy_networks(["10.0.0.2"])) == ipaddress.ip_address("10.0.0.2")


def test_untrusted_peer_does_not_even_consume_forwarded_values():
    def unsafe_input():
        raise AssertionError("Untrusted XFF must not be read")
        yield b"192.0.2.7"

    assert resolve_audit_ip("192.0.2.7", unsafe_input(), ()) == ipaddress.ip_address("192.0.2.7")


@pytest.mark.parametrize("peer", [None, "not-an-ip"])
def test_invalid_peer_omits_both_hash_fields(peer):
    context = build_http_audit_context(config=configuration(), method="GET", peer=peer).context
    assert context.ip_hash is None
    assert context.ip_hash_version is None


@pytest.mark.parametrize("peer", ["192.0.2.7", "2001:db8::7"])
def test_context_serialization_contains_only_safe_data(peer):
    state = build_http_audit_context(
        config=configuration(), method="GET", peer=peer, user_agent="Browser"
    )
    assert isinstance(state.context.request_id, UUID)
    assert state.context.correlation_id is None
    assert state.context.actor.tipo is TipoActorBitacora.ANONIMO
    assert state.context.ip_hash_version == 1
    assert set(state.context.model_dump()) == {
        "request_id", "correlation_id", "actor", "ip_hash", "ip_hash_version",
        "user_agent", "metodo_http", "ruta_http",
    }
    rendered = state.context.model_dump_json() + repr(state)
    for forbidden in (peer, KEY, "SecretStr", "Settings", "Request", "password", "Authorization"):
        assert forbidden not in rendered


def test_http_builder_normalizes_equivalent_ipv6_before_hmac():
    compact = build_http_audit_context(config=configuration(), method="GET", peer="2001:db8::7").context
    expanded = build_http_audit_context(
        config=configuration(), method="GET", peer="2001:0db8:0:0:0:0:0:7"
    ).context
    assert compact.ip_hash is not None
    assert expanded.ip_hash == compact.ip_hash


def test_xff_maximum_number_of_hops_is_accepted():
    header = b", ".join([b"192.0.2.7"] + [b"10.0.0.3"] * (MAX_XFF_HOPS - 1))
    assert resolve_audit_ip("10.0.0.2", [header], trusted_proxy_networks(["10.0.0.0/24"])) == ipaddress.ip_address("192.0.2.7")


@pytest.mark.parametrize("key", [None, "", "short", SecretStr(" " * 32)])
def test_enabled_without_valid_key_never_uses_plain_hash(key):
    context = build_http_audit_context(
        config=configuration(audit_ip_hmac_key=key), method="GET", peer="192.0.2.7"
    ).context
    assert context.ip_hash is None
    assert context.ip_hash_version is None


def test_disabled_audit_does_not_collect_identity_ip_or_agent():
    state = build_http_audit_context(
        config=configuration(audit_enabled=False),
        method="GET", peer="192.0.2.7", user_agent="private-agent",
    )
    bind_authenticated_actor(state, usuario_id=1, username="private-user", nombre="Private", rol="ADMIN")
    assert state.context.request_id is not None
    assert state.context.actor == ActorBitacora(tipo=TipoActorBitacora.ANONIMO)
    assert state.context.ip_hash is None
    assert state.context.ip_hash_version is None
    assert state.context.user_agent is None
    assert "private" not in state.context.model_dump_json()


def test_actor_binding_updates_the_same_context_seen_by_earlier_dependencies():
    state = build_http_audit_context(config=configuration(), method="GET", peer=None)
    earlier = state.context
    assert earlier.actor.tipo is TipoActorBitacora.ANONIMO
    bind_authenticated_actor(state, usuario_id=1, username="DatabaseUser", nombre="User Name", rol="ADMIN")
    assert state.context is earlier
    assert earlier.actor.tipo is TipoActorBitacora.USUARIO
    assert earlier.actor.username_snapshot == "DatabaseUser"


def test_internal_request_id_cannot_be_replaced_after_initialization():
    context = build_http_audit_context(config=configuration(), method="GET", peer=None).context
    original = context.request_id
    with pytest.raises(ValidationError):
        context.request_id = uuid4()
    assert context.request_id == original


def test_user_agent_uses_existing_sanitization_and_preserves_unicode():
    state = build_http_audit_context(
        config=configuration(), method="GET", peer=None,
        user_agent=" Navegador\x00\r\n\t  á日本語\x01\x7f  ",
    )
    assert state.context.user_agent == "Navegador á日本語"


@pytest.mark.parametrize("limit", [1, 17, 300])
def test_user_agent_obeys_configured_limit(limit):
    context = build_http_audit_context(
        config=configuration(audit_user_agent_max_length=limit),
        method="GET", peer=None, user_agent="á" * 400,
    ).context
    assert context.user_agent == "á" * limit


@pytest.mark.parametrize("template", [None, "/" + "a" * 255, "/unsafe?secret=value", "/bad\x00"])
def test_unresolved_or_invalid_template_never_uses_raw_path(template):
    state = build_http_audit_context(config=configuration(), method="GET", peer=None)
    refresh_audit_route(
        {"route": SimpleNamespace(path=template), "path": "/private-value", "query_string": b"token=secret"},
        state,
    )
    assert state.context.ruta_http == UNRESOLVED_ROUTE


def test_unsupported_long_method_is_omitted_without_breaking_request():
    assert build_http_audit_context(config=configuration(), method="CUSTOMMETHODLONG", peer=None).context.metodo_http is None


def test_system_context_generates_one_correlation_and_reuses_explicit_id(monkeypatch):
    from app.services import audit_context

    generated = uuid4()
    calls = []

    def generate():
        calls.append(True)
        return generated

    monkeypatch.setattr(audit_context, "uuid4", generate)
    context = build_system_audit_context()
    assert context.correlation_id == generated
    assert UUID(context.model_dump(mode="json")["correlation_id"]) == generated
    assert context.correlation_id == generated
    assert len(calls) == 1
    assert build_system_audit_context(generated).correlation_id == generated
    assert len(calls) == 1
    assert context.request_id is None
    assert context.actor == ActorBitacora(tipo=TipoActorBitacora.SISTEMA)
    assert all(getattr(context, field) is None for field in (
        "metodo_http", "ruta_http", "ip_hash", "ip_hash_version", "user_agent"
    ))


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"request_id": uuid4(), "ip_hash": "a" * 64},
        {"request_id": uuid4(), "ip_hash_version": 1},
        {"correlation_id": uuid4(), "metodo_http": "GET"},
    ],
)
def test_invalid_context_rejects_missing_id_and_inconsistent_fields(overrides):
    with pytest.raises(ValidationError):
        AuditContext(actor=ActorBitacora(tipo=TipoActorBitacora.ANONIMO), **overrides)


@pytest.mark.parametrize("system", [False, True])
def test_safe_context_is_compatible_with_closed_persistence_contract(system):
    context = build_system_audit_context() if system else build_http_audit_context(
        config=configuration(), method="GET", peer="192.0.2.7", user_agent="Browser"
    ).context
    event = BitacoraEventoCreateInternal(
        categoria="FUNCIONAL", actor=context.actor, modulo="PRUEBA", accion="CONSULTAR",
        resultado="EXITOSO", schema_version=1,
        request_id=context.request_id, correlation_id=context.correlation_id,
        ip_hash=context.ip_hash, ip_hash_version=context.ip_hash_version,
        user_agent=context.user_agent, metodo_http=context.metodo_http,
        ruta_template=context.ruta_http,
    )
    assert event.request_id == context.request_id
    assert event.correlation_id == context.correlation_id
