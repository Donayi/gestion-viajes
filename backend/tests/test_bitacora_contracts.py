import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.bitacora import (
    AUDIT_JSON_COMBINED_MAX_BYTES,
    AUDIT_JSON_MAX_ARRAY_ITEMS,
    AUDIT_JSON_MAX_BYTES,
    AUDIT_JSON_MAX_DEPTH,
    AUDIT_JSON_MAX_KEYS,
    AUDIT_JSON_MAX_KEY_LENGTH,
    AUDIT_JSON_MAX_STRING_LENGTH,
    AUDIT_USER_AGENT_MAX_LENGTH,
    AUDIT_USERNAME_MAX_LENGTH,
    ActorBitacora,
    CategoriaBitacora,
    DatosAuditoriaBitacora,
    ReferenciaRegistroBitacora,
    ResultadoBitacora,
    TipoActorBitacora,
    normalize_audit_username,
    sanitize_user_agent,
    serialize_audit_json,
    validate_combined_audit_json,
)


def test_enums_contain_exactly_the_approved_values():
    assert {item.value for item in CategoriaBitacora} == {"FUNCIONAL", "SEGURIDAD"}
    assert {item.value for item in TipoActorBitacora} == {"USUARIO", "ANONIMO", "SISTEMA"}
    assert {item.value for item in ResultadoBitacora} == {
        "EXITOSO",
        "FALLIDO",
        "RECHAZADO",
    }


def test_contracts_are_strict_and_catalog_names_are_extensible():
    actor = ActorBitacora(
        tipo="USUARIO",
        usuario_id=7,
        username_snapshot="Admin",
        nombre_snapshot="Ada Lovelace",
        rol_snapshot="ADMIN",
    )
    reference = ReferenciaRegistroBitacora(entidad_tipo="VIAJE_ESPECIAL", entidad_id="42")

    assert actor.tipo is TipoActorBitacora.USUARIO
    assert reference.entidad_tipo == "VIAJE_ESPECIAL"
    with pytest.raises(ValidationError):
        ActorBitacora(tipo="SISTEMA", unexpected=True)
    with pytest.raises(ValidationError):
        ReferenciaRegistroBitacora(entidad_tipo="Viaje", entidad_id="42")


def test_user_actor_requires_non_empty_identity_snapshots():
    valid = ActorBitacora(
        tipo="USUARIO",
        username_snapshot=" Admin ",
        nombre_snapshot=" Ada Lovelace ",
        rol_snapshot=" ADMIN ",
    )
    assert valid.username_snapshot == "Admin"
    assert valid.nombre_snapshot == "Ada Lovelace"
    assert valid.rol_snapshot == "ADMIN"

    for missing in ("username_snapshot", "nombre_snapshot", "rol_snapshot"):
        values = {
            "tipo": "USUARIO",
            "username_snapshot": "Admin",
            "nombre_snapshot": "Ada Lovelace",
            "rol_snapshot": "ADMIN",
        }
        values[missing] = "   "
        with pytest.raises(ValidationError, match="requiere username, nombre y rol"):
            ActorBitacora(**values)


@pytest.mark.parametrize("actor_type", ["ANONIMO", "SISTEMA"])
def test_non_user_actors_cannot_include_user_id(actor_type):
    with pytest.raises(ValidationError, match="Solo un actor USUARIO"):
        ActorBitacora(tipo=actor_type, usuario_id=7)


def test_anonymous_actor_can_keep_normalized_failed_login_username():
    actor = ActorBitacora(tipo="ANONIMO", username_snapshot="  Admin.Intentado  ")
    assert actor.username_snapshot == "Admin.Intentado"


def test_actor_name_snapshot_limit_and_extra_fields_are_enforced():
    ActorBitacora(tipo="ANONIMO", nombre_snapshot="n" * 301)
    with pytest.raises(ValidationError):
        ActorBitacora(tipo="ANONIMO", nombre_snapshot="n" * 302)
    with pytest.raises(ValidationError):
        ActorBitacora(tipo="ANONIMO", password="secret")


def test_json_serialization_is_canonical_compact_and_unicode():
    assert serialize_audit_json({"z": "á", "a": [True, None, 1]}) == (
        '{"a":[true,null,1],"z":"á"}'
    )


@pytest.mark.parametrize(
    "value",
    [
        1.0,
        1.5,
        float("nan"),
        float("inf"),
        Decimal("1.5"),
        date(2026, 8, 13),
        datetime(2026, 8, 13, 12, 0),
        b"secret",
        (1, 2),
        object(),
    ],
)
def test_json_rejects_every_unapproved_type(value):
    with pytest.raises(TypeError, match="tipo no autorizado"):
        serialize_audit_json({"value": value})


def test_json_rejects_orm_like_objects():
    class FakeOrm:
        id = 1

    with pytest.raises(TypeError, match="tipo no autorizado"):
        serialize_audit_json({"value": FakeOrm()})


def test_json_rejects_cycles():
    cyclic = []
    cyclic.append(cyclic)

    with pytest.raises(ValueError, match="ciclos"):
        serialize_audit_json(cyclic)


def test_json_depth_accepts_four_and_rejects_five_container_levels():
    accepted = {"one": [{"three": ["value"]}]}
    rejected = {"one": [{"three": [["value"]]}]}

    serialize_audit_json(accepted)
    with pytest.raises(ValueError, match=f"profundidad {AUDIT_JSON_MAX_DEPTH}"):
        serialize_audit_json(rejected)


def test_json_key_count_is_recursive_and_bounded():
    serialize_audit_json({str(index): index for index in range(AUDIT_JSON_MAX_KEYS)})
    with pytest.raises(ValueError, match=f"{AUDIT_JSON_MAX_KEYS} claves"):
        serialize_audit_json(
            {str(index): index for index in range(AUDIT_JSON_MAX_KEYS + 1)}
        )


def test_json_key_length_is_bounded():
    serialize_audit_json({"k" * AUDIT_JSON_MAX_KEY_LENGTH: True})
    with pytest.raises(ValueError, match=f"{AUDIT_JSON_MAX_KEY_LENGTH} caracteres"):
        serialize_audit_json({"k" * (AUDIT_JSON_MAX_KEY_LENGTH + 1): True})


def test_json_string_length_is_bounded():
    serialize_audit_json("á" * AUDIT_JSON_MAX_STRING_LENGTH)
    with pytest.raises(ValueError, match=f"{AUDIT_JSON_MAX_STRING_LENGTH} caracteres"):
        serialize_audit_json("á" * (AUDIT_JSON_MAX_STRING_LENGTH + 1))


def test_json_array_length_is_bounded():
    serialize_audit_json([None] * AUDIT_JSON_MAX_ARRAY_ITEMS)
    with pytest.raises(ValueError, match=f"{AUDIT_JSON_MAX_ARRAY_ITEMS} elementos"):
        serialize_audit_json([None] * (AUDIT_JSON_MAX_ARRAY_ITEMS + 1))


def test_json_document_size_is_measured_in_utf8_bytes_without_truncation():
    value = "á" * 10
    exact_size = len(serialize_audit_json(value).encode("utf-8"))

    assert serialize_audit_json(value, max_bytes=exact_size)
    with pytest.raises(ValueError, match="bytes UTF-8"):
        serialize_audit_json(value, max_bytes=exact_size - 1)


def test_default_json_document_limit_is_8192_bytes():
    document = {f"k{index:02}": "x" * 500 for index in range(16)}
    base_size = len(
        json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    empty_padding_cost = len(',"padding":""'.encode("utf-8"))
    padding_length = AUDIT_JSON_MAX_BYTES - base_size - empty_padding_cost
    document["padding"] = "x" * padding_length

    assert len(serialize_audit_json(document).encode("utf-8")) == AUDIT_JSON_MAX_BYTES
    document["padding"] += "x"
    with pytest.raises(ValueError, match=str(AUDIT_JSON_MAX_BYTES)):
        serialize_audit_json(document)


def test_combined_json_size_limit_is_enforced():
    documents = ({"value": "x" * 400},) * 3
    serialized = validate_combined_audit_json(
        *documents,
        max_document_bytes=AUDIT_JSON_MAX_BYTES,
        max_combined_bytes=AUDIT_JSON_COMBINED_MAX_BYTES,
    )
    exact_size = sum(len(item.encode("utf-8")) for item in serialized)

    validate_combined_audit_json(*documents, max_combined_bytes=exact_size)
    with pytest.raises(ValueError, match="límite combinado"):
        validate_combined_audit_json(*documents, max_combined_bytes=exact_size - 1)


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_combined_json_accepts_zero_to_three_documents(count):
    documents = tuple({"index": index} for index in range(count))
    assert len(validate_combined_audit_json(*documents)) == count


def test_combined_json_rejects_more_than_three_documents():
    with pytest.raises(ValueError, match="tres documentos"):
        validate_combined_audit_json({}, {}, {}, {})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_document_bytes": 0},
        {"max_document_bytes": -1},
        {"max_combined_bytes": 0},
        {"max_combined_bytes": -1},
    ],
)
def test_combined_json_rejects_non_positive_limits(kwargs):
    with pytest.raises(ValueError, match="mayor que cero"):
        validate_combined_audit_json({}, **kwargs)


def test_empty_json_documents_are_valid_and_counted_when_present():
    assert validate_combined_audit_json({}, [], None) == ("{}", "[]", "null")


def test_audit_data_contract_validates_all_three_json_documents():
    contract = DatosAuditoriaBitacora(
        valores_anteriores={"estado": "CREADO"},
        valores_posteriores={"estado": "ASIGNADO"},
        datos_evento={"motivo": "asignación"},
    )

    assert contract.valores_posteriores == {"estado": "ASIGNADO"}
    with pytest.raises(ValidationError, match="tipo no autorizado"):
        DatosAuditoriaBitacora(datos_evento={"value": b"secret"})


def test_audit_data_contract_enforces_combined_size_and_ignores_absent_documents():
    large_document = {f"k{index:02}": "x" * 500 for index in range(12)}
    DatosAuditoriaBitacora(valores_anteriores=large_document)
    DatosAuditoriaBitacora(
        valores_anteriores=large_document,
        valores_posteriores=large_document,
    )
    with pytest.raises(ValidationError, match="límite combinado"):
        DatosAuditoriaBitacora(
            valores_anteriores=large_document,
            valores_posteriores=large_document,
            datos_evento=large_document,
        )
    assert DatosAuditoriaBitacora().model_dump() == {
        "valores_anteriores": None,
        "valores_posteriores": None,
        "datos_evento": None,
    }


def test_user_agent_removes_controls_normalizes_spaces_and_truncates():
    raw = "  Mozilla\x00/5.0\r\n  Browser\t Name  "

    assert sanitize_user_agent(raw) == "Mozilla/5.0 Browser Name"
    assert sanitize_user_agent("abcdef", max_length=4) == "abcd"
    assert sanitize_user_agent(None) is None
    assert AUDIT_USER_AGENT_MAX_LENGTH == 300


def test_user_agent_requires_a_positive_limit():
    with pytest.raises(ValueError, match="mayor que cero"):
        sanitize_user_agent("agent", max_length=0)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Mozilla\x00/5.0", "Mozilla/5.0"),
        ("A\rB\nC\tD", "A B C D"),
        ("A\x01B\x1fC", "ABC"),
        (" Navegador ágil 日本語 ", "Navegador ágil 日本語"),
    ],
)
def test_user_agent_sanitization_rules(raw, expected):
    assert sanitize_user_agent(raw) == expected


def test_user_agent_rejects_non_string_values():
    with pytest.raises(TypeError, match="User-Agent"):
        sanitize_user_agent(123)


def test_username_is_trimmed_truncated_and_case_preserved():
    assert normalize_audit_username("  Admin.User  ") == "Admin.User"
    assert normalize_audit_username("A" * 151) == "A" * AUDIT_USERNAME_MAX_LENGTH
    assert normalize_audit_username("CaseSensitive") != "casesensitive"


def test_username_boundaries_empty_values_and_invalid_type():
    exact = "A" * AUDIT_USERNAME_MAX_LENGTH
    assert normalize_audit_username("  User.Name  ") == "User.Name"
    assert normalize_audit_username("CaseSensitive") == "CaseSensitive"
    assert normalize_audit_username(exact) == exact
    assert normalize_audit_username(exact + "B") == exact
    assert normalize_audit_username("") == ""
    assert normalize_audit_username("   ") == ""
    with pytest.raises(TypeError, match="username"):
        normalize_audit_username(123)
