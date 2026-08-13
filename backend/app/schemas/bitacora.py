import json
import unicodedata
from enum import StrEnum
from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


AUDIT_JSON_MAX_BYTES = 8192
AUDIT_JSON_COMBINED_MAX_BYTES = 16384
AUDIT_JSON_MAX_DEPTH = 4
AUDIT_JSON_MAX_KEYS = 64
AUDIT_JSON_MAX_KEY_LENGTH = 64
AUDIT_JSON_MAX_STRING_LENGTH = 500
AUDIT_JSON_MAX_ARRAY_ITEMS = 50
AUDIT_USER_AGENT_MAX_LENGTH = 300
AUDIT_USERNAME_MAX_LENGTH = 150

JsonScalar: TypeAlias = None | bool | int | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
CatalogoBitacora = Annotated[
    str,
    Field(min_length=1, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$"),
]


class BitacoraContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CategoriaBitacora(StrEnum):
    FUNCIONAL = "FUNCIONAL"
    SEGURIDAD = "SEGURIDAD"


class TipoActorBitacora(StrEnum):
    USUARIO = "USUARIO"
    ANONIMO = "ANONIMO"
    SISTEMA = "SISTEMA"


class ResultadoBitacora(StrEnum):
    EXITOSO = "EXITOSO"
    FALLIDO = "FALLIDO"
    RECHAZADO = "RECHAZADO"


class ActorBitacora(BitacoraContract):
    tipo: TipoActorBitacora
    usuario_id: int | None = Field(default=None, ge=1)
    username_snapshot: str | None = Field(default=None, max_length=150)
    rol_snapshot: str | None = Field(default=None, max_length=100)
    nombre_snapshot: str | None = Field(default=None, max_length=301)

    @model_validator(mode="after")
    def validate_actor_identity(self) -> "ActorBitacora":
        if self.tipo is TipoActorBitacora.USUARIO:
            required = (
                self.username_snapshot,
                self.nombre_snapshot,
                self.rol_snapshot,
            )
            if any(value is None or not value.strip() for value in required):
                raise ValueError(
                    "Un actor USUARIO requiere username, nombre y rol no vacíos"
                )
        elif self.usuario_id is not None:
            raise ValueError("Solo un actor USUARIO puede incluir usuario_id")
        return self


class ReferenciaRegistroBitacora(BitacoraContract):
    entidad_tipo: CatalogoBitacora
    entidad_id: str = Field(min_length=1, max_length=100)


def _validate_json_value(
    value: object,
    *,
    depth: int,
    ancestors: set[int],
    key_count: list[int],
) -> None:
    value_type = type(value)
    if value is None or value_type in {bool, int}:
        return
    if value_type is str:
        if len(value) > AUDIT_JSON_MAX_STRING_LENGTH:
            raise ValueError(
                f"Los strings JSON no pueden exceder {AUDIT_JSON_MAX_STRING_LENGTH} caracteres"
            )
        return
    if value_type not in {list, dict}:
        raise TypeError("Los documentos de bitácora contienen un tipo no autorizado")
    if depth > AUDIT_JSON_MAX_DEPTH:
        raise ValueError(
            f"Los documentos JSON no pueden exceder profundidad {AUDIT_JSON_MAX_DEPTH}"
        )

    identity = id(value)
    if identity in ancestors:
        raise ValueError("Los documentos de bitácora no aceptan ciclos")
    ancestors.add(identity)
    try:
        if value_type is list:
            if len(value) > AUDIT_JSON_MAX_ARRAY_ITEMS:
                raise ValueError(
                    f"Los arrays JSON no pueden exceder {AUDIT_JSON_MAX_ARRAY_ITEMS} elementos"
                )
            for item in value:
                _validate_json_value(
                    item,
                    depth=depth + 1,
                    ancestors=ancestors,
                    key_count=key_count,
                )
            return

        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("Todas las claves JSON deben ser strings")
            if len(key) > AUDIT_JSON_MAX_KEY_LENGTH:
                raise ValueError(
                    f"Las claves JSON no pueden exceder {AUDIT_JSON_MAX_KEY_LENGTH} caracteres"
                )
            key_count[0] += 1
            if key_count[0] > AUDIT_JSON_MAX_KEYS:
                raise ValueError(
                    f"Los documentos JSON no pueden exceder {AUDIT_JSON_MAX_KEYS} claves"
                )
            _validate_json_value(
                item,
                depth=depth + 1,
                ancestors=ancestors,
                key_count=key_count,
            )
    finally:
        ancestors.remove(identity)


def serialize_audit_json(
    value: JsonValue,
    *,
    max_bytes: int = AUDIT_JSON_MAX_BYTES,
) -> str:
    if max_bytes <= 0:
        raise ValueError("max_bytes debe ser mayor que cero")
    _validate_json_value(value, depth=1, ancestors=set(), key_count=[0])
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    size = len(serialized.encode("utf-8"))
    if size > max_bytes:
        raise ValueError(f"El documento JSON excede el límite de {max_bytes} bytes UTF-8")
    return serialized


def validate_combined_audit_json(
    *documents: JsonValue,
    max_document_bytes: int = AUDIT_JSON_MAX_BYTES,
    max_combined_bytes: int = AUDIT_JSON_COMBINED_MAX_BYTES,
) -> tuple[str, ...]:
    if len(documents) > 3:
        raise ValueError("Solo se permiten los tres documentos JSON aprobados")
    if max_document_bytes <= 0:
        raise ValueError("max_document_bytes debe ser mayor que cero")
    if max_combined_bytes <= 0:
        raise ValueError("max_combined_bytes debe ser mayor que cero")
    serialized = tuple(
        serialize_audit_json(document, max_bytes=max_document_bytes)
        for document in documents
    )
    combined_size = sum(len(document.encode("utf-8")) for document in serialized)
    if combined_size > max_combined_bytes:
        raise ValueError(
            f"Los documentos JSON exceden el límite combinado de {max_combined_bytes} bytes UTF-8"
        )
    return serialized


class DatosAuditoriaBitacora(BitacoraContract):
    valores_anteriores: dict[str, object] | None = None
    valores_posteriores: dict[str, object] | None = None
    datos_evento: dict[str, object] | None = None

    @model_validator(mode="after")
    def validate_json_documents(self) -> "DatosAuditoriaBitacora":
        documents = [
            document
            for document in (
                self.valores_anteriores,
                self.valores_posteriores,
                self.datos_evento,
            )
            if document is not None
        ]
        try:
            validate_combined_audit_json(*documents)
        except TypeError as exc:
            raise ValueError(
                "Los documentos de bitácora contienen un tipo no autorizado"
            ) from exc
        return self


def sanitize_user_agent(
    value: str | None,
    *,
    max_length: int = AUDIT_USER_AGENT_MAX_LENGTH,
) -> str | None:
    if max_length <= 0:
        raise ValueError("max_length debe ser mayor que cero")
    if value is None:
        return None
    if type(value) is not str:
        raise TypeError("User-Agent debe ser un string")
    sanitized: list[str] = []
    for character in value:
        if character == "\x00":
            continue
        if character in {"\t", "\n", "\r"}:
            sanitized.append(" ")
            continue
        if unicodedata.category(character) == "Cc":
            continue
        sanitized.append(character)
    without_controls = "".join(sanitized)
    normalized = " ".join(without_controls.split())
    return normalized[:max_length]


def normalize_audit_username(value: str) -> str:
    if type(value) is not str:
        raise TypeError("username debe ser un string")
    return value.strip()[:AUDIT_USERNAME_MAX_LENGTH]


__all__ = [
    "AUDIT_JSON_COMBINED_MAX_BYTES",
    "AUDIT_JSON_MAX_ARRAY_ITEMS",
    "AUDIT_JSON_MAX_BYTES",
    "AUDIT_JSON_MAX_DEPTH",
    "AUDIT_JSON_MAX_KEYS",
    "AUDIT_JSON_MAX_KEY_LENGTH",
    "AUDIT_JSON_MAX_STRING_LENGTH",
    "AUDIT_USER_AGENT_MAX_LENGTH",
    "AUDIT_USERNAME_MAX_LENGTH",
    "ActorBitacora",
    "BitacoraContract",
    "CatalogoBitacora",
    "CategoriaBitacora",
    "DatosAuditoriaBitacora",
    "JsonValue",
    "ReferenciaRegistroBitacora",
    "ResultadoBitacora",
    "TipoActorBitacora",
    "normalize_audit_username",
    "sanitize_user_agent",
    "serialize_audit_json",
    "validate_combined_audit_json",
]
