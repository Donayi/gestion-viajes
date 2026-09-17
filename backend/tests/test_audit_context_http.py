import ast
import asyncio
import inspect
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.deps_audit import get_audit_context
from app.bootstrap.audit_context import AuditContextMiddleware
from app.core.config import Settings, settings
from app.schemas.audit_context import AuditContext
from app.services.audit_context import UNRESOLVED_ROUTE, get_audit_state


KEY = "http-test-audit-key-at-least-32-bytes"


class ObserveContext:
    """Test boundary observes errors too, without changing the real middleware."""

    def __init__(self, app):
        self.app = app
        self.contexts = []

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        finally:
            state = get_audit_state(scope)
            if state is not None:
                self.contexts.append(state.context)


@pytest.fixture
def audited_app(app, monkeypatch):
    monkeypatch.setattr(settings, "audit_enabled", True)
    monkeypatch.setattr(settings, "audit_ip_hmac_key", SecretStr(KEY))
    monkeypatch.setattr(settings, "audit_ip_hash_version", 1)
    monkeypatch.setattr(settings, "audit_trusted_proxies", [])
    monkeypatch.setattr(settings, "audit_user_agent_max_length", 300)

    @app.get("/_test/context/{item}")
    def context_endpoint(request: Request, context: AuditContext = Depends(get_audit_context)):
        again = get_audit_context(request)
        assert again.request_id == context.request_id
        return context.model_dump(mode="json")

    return app


def test_request_id_exists_is_unique_and_ignores_all_external_ids(audited_app):
    client = TestClient(audited_app)
    external = str(uuid4())
    results = [
        client.get("/_test/context/one").json(),
        client.get("/_test/context/two", headers={"X-Request-ID": external}).json(),
        client.get("/_test/context/three", headers={
            "X-Request-ID": "invalid-'; DROP TABLE usuarios;--",
            "Request-ID": external,
            "Correlation-ID": external,
            "X-Correlation-ID": external,
        }).json(),
    ]
    identifiers = [UUID(result["request_id"]) for result in results]
    assert len(set(identifiers)) == 3
    assert UUID(external) not in identifiers
    assert all(result["correlation_id"] is None for result in results)
    assert all(result["actor"]["tipo"] == "ANONIMO" for result in results)


def test_method_and_template_never_include_parameters_or_query(audited_app):
    secret = "private-record-value"
    response = TestClient(audited_app).get(f"/_test/context/{secret}?password=query-secret")
    assert response.status_code == 200
    context = response.json()
    assert context["metodo_http"] == "GET"
    assert context["ruta_http"] == "/_test/context/{item}"
    assert secret not in response.text
    assert "query-secret" not in response.text


def test_404_keeps_safe_marker(audited_app):
    observer = ObserveContext(audited_app)
    response = TestClient(observer).get("/not-found/private-value?token=private-query")
    assert response.status_code == 404
    assert observer.contexts[-1].ruta_http == UNRESOLVED_ROUTE
    assert "private" not in observer.contexts[-1].model_dump_json()


def test_context_survives_server_error_without_masking_it(audited_app):
    @audited_app.get("/_test/error")
    def error():
        raise RuntimeError("test failure")

    observer = ObserveContext(audited_app)
    response = TestClient(observer, raise_server_exceptions=False).get("/_test/error")
    assert response.status_code == 500
    assert observer.contexts[-1].request_id is not None
    assert observer.contexts[-1].ruta_http == "/_test/error"
    assert "codigo_http" not in observer.contexts[-1].model_dump()


def test_cors_preflight_has_its_own_context(audited_app):
    observer = ObserveContext(audited_app)
    response = TestClient(observer).options("/_test/context/item", headers={
        "Origin": settings.cors_allowed_origins[0],
        "Access-Control-Request-Method": "GET",
    })
    assert response.status_code == 200
    assert observer.contexts[-1].request_id is not None
    assert observer.contexts[-1].metodo_http == "OPTIONS"
    assert observer.contexts[-1].ruta_http == UNRESOLVED_ROUTE


def test_concurrent_requests_have_separate_stable_contexts(audited_app):
    async def run():
        ready = asyncio.Event()
        entered = []

        @audited_app.get("/_test/concurrent/{item}")
        async def concurrent(request: Request, context: AuditContext = Depends(get_audit_context)):
            entered.append(context.request_id)
            if len(entered) == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), timeout=5)
            assert get_audit_context(request).request_id == context.request_id
            return context.model_dump(mode="json")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=audited_app), base_url="http://test"
        ) as client:
            first, second = await asyncio.gather(
                client.get("/_test/concurrent/one", headers={"User-Agent": "agent-one"}),
                client.get("/_test/concurrent/two", headers={"User-Agent": "agent-two"}),
            )
        assert first.status_code == second.status_code == 200
        assert first.json()["request_id"] != second.json()["request_id"]
        assert first.json()["user_agent"] == "agent-one"
        assert second.json()["user_agent"] == "agent-two"

    asyncio.run(run())


def run_middleware(*, peer, headers=(), enabled=True, proxies=(), key=KEY):
    config = Settings(
        _env_file=None, database_url="postgresql+psycopg://test:test@invalid/test",
        app_env="test", environment=None,
        audit_enabled=enabled, audit_ip_hmac_key=key,
        audit_ip_hash_version=1, audit_trusted_proxies=list(proxies),
        audit_user_agent_max_length=300,
    )
    scope = {
        "type": "http", "method": "POST", "path": "/private-path",
        "query_string": b"password=private-query",
        "client": (peer, 1234) if peer is not None else None,
        "headers": list(headers),
    }
    observed = []
    messages = []

    async def endpoint(scope, receive, send):
        observed.append(get_audit_state(scope).context)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        raise AssertionError("Context middleware must not read the body")

    async def send(message):
        messages.append(message)

    asyncio.run(AuditContextMiddleware(endpoint, config)(scope, receive, send))
    assert messages[-1]["body"] == b"ok"
    return observed[0]


def test_middleware_does_not_collect_secrets_or_unapproved_headers():
    context = run_middleware(peer="192.0.2.7", headers=[
        (b"authorization", b"Bearer private-jwt"),
        (b"cookie", b"session=private-cookie"),
        (b"x-secret", b"private-header"),
        (b"forwarded", b"for=198.51.100.9"),
        (b"x-real-ip", b"198.51.100.9"),
        (b"user-agent", b"Browser"),
    ])
    assert context.user_agent == "Browser"
    serialized = context.model_dump_json() + repr(context)
    for forbidden in (
        "192.0.2.7", "198.51.100.9", KEY, "private", "authorization", "cookie",
        "SecretStr", "Settings", "Request", "Session", "Usuario",
    ):
        assert forbidden not in serialized
    assert context.ip_hash == run_middleware(peer="192.0.2.7").ip_hash


def test_raw_asgi_user_agent_controls_are_sanitized():
    context = run_middleware(peer=None, headers=[
        (b"user-agent", b"Browser\x00\r\n\t v1\x01\x7f"),
    ])
    assert context.user_agent == "Browser v1"


def test_raw_malicious_identifier_headers_are_never_reused():
    external = str(uuid4())
    context = run_middleware(peer=None, headers=[
        (b"x-request-id", external.encode("ascii")),
        (b"request-id", b"\x00\r\n"),
        (b"correlation-id", external.encode("ascii")),
    ])
    assert context.request_id != UUID(external)
    assert context.correlation_id is None


def test_duplicate_user_agent_is_omitted():
    context = run_middleware(peer=None, headers=[
        (b"user-agent", b"one"), (b"user-agent", b"two"),
    ])
    assert context.user_agent is None


def test_xff_is_only_processed_for_configured_peer():
    headers = [(b"x-forwarded-for", b"192.0.2.7")]
    direct = run_middleware(peer="10.0.0.2")
    untrusted = run_middleware(peer="10.0.0.2", headers=headers)
    trusted = run_middleware(peer="10.0.0.2", headers=headers, proxies=["10.0.0.0/24"])
    assert untrusted.ip_hash == direct.ip_hash
    assert trusted.ip_hash == run_middleware(peer="192.0.2.7").ip_hash
    assert trusted.ip_hash != direct.ip_hash


def test_disabled_middleware_keeps_id_without_collecting_headers_or_ip():
    context = run_middleware(peer="192.0.2.7", headers=[(b"user-agent", b"private-agent")], enabled=False)
    assert context.request_id is not None
    assert context.ip_hash is None
    assert context.ip_hash_version is None
    assert context.user_agent is None
    assert context.actor.tipo.value == "ANONIMO"


def test_middleware_without_key_omits_hash_pair():
    context = run_middleware(peer="192.0.2.7", key=None)
    assert context.ip_hash is None
    assert context.ip_hash_version is None


def test_non_http_scope_passes_through_untouched():
    seen = []
    scope = {"type": "lifespan"}

    async def endpoint(scope, receive, send):
        seen.append(scope)

    async def unused():
        raise AssertionError("not needed")

    config = Settings(
        _env_file=None, database_url="postgresql+psycopg://test:test@invalid/test",
        app_env="test", environment=None, audit_enabled=False, audit_ip_hmac_key=None,
        audit_trusted_proxies=[], audit_ip_hash_version=1, audit_user_agent_max_length=300,
    )
    asyncio.run(AuditContextMiddleware(endpoint, config)(scope, unused, unused))
    assert seen == [scope]
    assert "state" not in scope


def test_missing_middleware_is_reported_without_generating_parallel_id():
    with pytest.raises(RuntimeError, match="middleware"):
        get_audit_context(Request({"type": "http", "state": {}}))


def test_context_layer_has_no_database_or_persistence_dependencies(monkeypatch):
    from app.crud import crud_bitacora

    def forbidden(*args, **kwargs):
        raise AssertionError("Audit context must not persist anything")

    for name in ("create_bitacora_evento", "get_bitacora_evento_by_id", "list_bitacora_eventos"):
        monkeypatch.setattr(crud_bitacora, name, forbidden)
    assert run_middleware(peer="192.0.2.7").request_id is not None

    from app.api import deps_audit
    from app.bootstrap import audit_context as middleware_module
    from app.schemas import audit_context as schema_module
    from app.services import audit_context as service_module

    # Complement the runtime guard with dependency/call inspection, not full-text matching.
    for module in (deps_audit, middleware_module, schema_module, service_module):
        tree = ast.parse(Path(inspect.getfile(module)).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("sqlalchemy", "app.db", "app.crud"))
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith(("sqlalchemy", "app.db", "app.crud")) for alias in node.names)
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                assert name not in {"commit", "rollback", "execute", "flush", "Session", "delete"}
