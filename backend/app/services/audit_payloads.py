"""Defensive JSON copying; operation-specific allowlists belong to instrumentation."""

import json
import unicodedata
from dataclasses import dataclass

from app.schemas.bitacora import AUDIT_JSON_MAX_BYTES, validate_combined_audit_json
from app.services.audit_errors import AuditPayloadError


SENSITIVE_KEYS = frozenset({
    "password", "passwd", "pwd", "token", "accesstoken", "refreshtoken",
    "authorization", "cookie", "setcookie", "secret", "apikey",
    "clientsecret", "privatekey", "headers", "requestheaders",
    "credenciales", "credentials",
})


def _check_string(value: str) -> None:
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise AuditPayloadError()
    # Reject lone surrogates, rather than leaking an invalid value into JSONB.
    value.encode("utf-8", errors="strict")


def validate_audit_string(value: str | None) -> None:
    """The same control policy for non-JSON fields; UA has its own sanitizer."""
    if value is None:
        return
    try:
        if not isinstance(value, str):
            raise AuditPayloadError()
        _check_string(value)
    except UnicodeError as exc:
        raise AuditPayloadError() from exc


def _inspect(value, depth=1) -> None:
    if type(value) is str:
        _check_string(value)
    elif type(value) is dict:
        if depth > 4:
            raise AuditPayloadError()
        for key, item in value.items():
            _check_string(key)
            normalized = "".join(
                character for character in unicodedata.normalize("NFKC", key).casefold()
                if character.isalnum()
            )
            if normalized in SENSITIVE_KEYS:
                raise AuditPayloadError()
            _inspect(item, depth + 1)
    elif type(value) is list:
        if depth > 4:
            raise AuditPayloadError()
        for item in value:
            _inspect(item, depth + 1)


@dataclass(frozen=True)
class AuditPayloads:
    valores_anteriores: dict | None
    valores_posteriores: dict | None
    datos_evento: dict | None


def copy_audit_payloads(
    *, valores_anteriores=None, valores_posteriores=None, datos_evento=None,
    max_document_bytes=AUDIT_JSON_MAX_BYTES,
) -> AuditPayloads:
    """Validate closed structural limits first, then reject sensitive/control data."""
    try:
        if not 1 <= max_document_bytes <= AUDIT_JSON_MAX_BYTES:
            raise AuditPayloadError()
        documents = (valores_anteriores, valores_posteriores, datos_evento)
        present = []
        for document in documents:
            if document is not None:
                if type(document) is not dict:
                    raise AuditPayloadError()
                present.append(document)
        serialized = validate_combined_audit_json(
            *present, max_document_bytes=max_document_bytes,
        )
        snapshots = [json.loads(document) for document in serialized]
        # Check the copies actually persisted, not mutable caller dictionaries.
        validate_combined_audit_json(*snapshots, max_document_bytes=max_document_bytes)
        for document in snapshots:
            _inspect(document)
        copied = iter(snapshots)
        return AuditPayloads(*(None if document is None else next(copied) for document in documents))
    except AuditPayloadError:
        raise
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise AuditPayloadError() from exc
