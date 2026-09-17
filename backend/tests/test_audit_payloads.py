from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.services.audit_errors import AuditPayloadError
from app.services.audit_payloads import copy_audit_payloads


@pytest.mark.parametrize("key", [
    "password", "PASSWORD", "passwd", "pwd", "token", "Access_Token",
    "refresh_token", "Authorization", "Cookie", "set-cookie", "secret",
    "api_key", "apikey", "client_secret", "private_key", "access token",
    "ＡＵＴＨＯＲＩＺＡＴＩＯＮ", "headers", "request_headers",
])
@pytest.mark.parametrize("location", ["root", "nested", "list"])
def test_sensitive_keys_are_rejected_everywhere(key, location):
    payload = {key: "secret-marker"}
    if location == "nested":
        payload = {"usuario": payload}
    elif location == "list":
        payload = {"items": [payload]}
    with pytest.raises(AuditPayloadError) as captured:
        copy_audit_payloads(datos_evento=payload)
    assert "secret-marker" not in str(captured.value)


@pytest.mark.parametrize("value", [
    1.5, float("nan"), float("inf"), Decimal("1"), b"bytes", uuid4(),
    datetime.now(UTC), SecretStr("secret-marker"), object(), (1, 2),
])
def test_unapproved_types_rejected(value):
    with pytest.raises(AuditPayloadError):
        copy_audit_payloads(datos_evento={"value": value})


def test_orm_and_request_are_not_serialized():
    from app.models.models import Usuario
    from starlette.requests import Request

    for value in (Usuario(username="private-user"), Request({"type": "http"})):
        with pytest.raises(AuditPayloadError):
            copy_audit_payloads(datos_evento={"value": value})


@pytest.mark.parametrize("control", ["\x00", "\x01", "\t", "\r", "\n", "\x1f", "\x7f", "\x85", "\x9f", "\ud800"])
@pytest.mark.parametrize("in_key", [False, True])
def test_controls_and_invalid_unicode_rejected(control, in_key):
    payload = {f"field{control}": "value"} if in_key else {"field": f"value{control}"}
    with pytest.raises(AuditPayloadError):
        copy_audit_payloads(datos_evento=payload)


def test_unicode_none_empty_dict_and_defensive_copy():
    original = {"items": [{"value": "á日本語", "nothing": None}], "count": 1, "flag": True}
    copied = copy_audit_payloads(valores_anteriores=None, valores_posteriores={}, datos_evento=original)
    original["items"][0]["value"] = "changed"
    original["items"].append({"token": "introduced-later"})
    assert copied.valores_anteriores is None
    assert copied.valores_posteriores == {}
    assert copied.datos_evento == {"items": [{"value": "á日本語", "nothing": None}], "count": 1, "flag": True}
    assert copy_audit_payloads().datos_evento is None


def test_no_semantic_string_scanning():
    assert copy_audit_payloads(datos_evento={"description": "the word token"}).datos_evento == {
        "description": "the word token"
    }


@pytest.mark.parametrize("payload", [
    {"value": "x" * 501}, {"k" * 65: 1}, {str(i): i for i in range(65)},
    {"items": list(range(51))}, {"a": {"b": {"c": {"d": {}}}}},
])
def test_structural_limits_rejected_without_truncation(payload):
    with pytest.raises(AuditPayloadError):
        copy_audit_payloads(datos_evento=payload)


def test_structural_boundaries_accepted():
    for payload in (
        {"value": "x" * 500}, {"k" * 64: 1}, {str(i): i for i in range(64)},
        {"items": list(range(50))}, {"a": {"b": {"c": {}}}},
    ):
        assert copy_audit_payloads(datos_evento=payload).datos_evento == payload


def _document(size):
    # 16 strings, each <= 500; tune the last string to the exact encoded size.
    import json

    payload = {f"k{i:02}": "x" * 500 for i in range(16)}
    base = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    payload["last"] = "x" * (size - base - 10)
    assert len(json.dumps(payload, separators=(",", ":")).encode("utf-8")) == size
    return payload


def test_document_bytes_exact_and_oversized():
    assert copy_audit_payloads(datos_evento=_document(8192)).datos_evento is not None
    with pytest.raises(AuditPayloadError):
        copy_audit_payloads(datos_evento=_document(8193))
    with pytest.raises(AuditPayloadError):
        copy_audit_payloads(datos_evento={"value": "á" * 100}, max_document_bytes=100)


def test_combined_limit_exact_and_oversized():
    copy_audit_payloads(valores_anteriores=_document(8192), valores_posteriores=_document(8192))
    with pytest.raises(AuditPayloadError):
        copy_audit_payloads(
            valores_anteriores=_document(8192), valores_posteriores=_document(8192), datos_evento={},
        )


def test_cycles_and_non_dictionary_roots_rejected():
    cyclic = {}
    cyclic["self"] = cyclic
    for value in (cyclic, [], "string", 1):
        with pytest.raises(AuditPayloadError):
            copy_audit_payloads(datos_evento=value)
