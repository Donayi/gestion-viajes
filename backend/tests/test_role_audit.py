from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.crud import crud_roles
from app.schemas.role import RoleCreate, RoleUpdate
from app.services import role_audit
from app.services.audit_payloads import copy_audit_payloads


def role():
    return SimpleNamespace(id_rol=17, nombre="ADMIN", descripcion="Description", usuarios=["excluded"])


def test_snapshot_allowlist_and_sanitizer():
    snapshot = role_audit.snapshot_role(role())
    assert snapshot == {"nombre": "ADMIN", "descripcion": "Description"}
    copied = copy_audit_payloads(valores_anteriores=None, valores_posteriores=snapshot,
                                 datos_evento=None, max_document_bytes=8192)
    assert copied.valores_posteriores == snapshot and "usuarios" not in snapshot


@pytest.mark.parametrize("fields,changed", [
    ({}, False), ({"nombre": "ADMIN"}, False), ({"descripcion": "Description"}, False),
    ({"nombre": "admin"}, True), ({"nombre": " ADMIN "}, True),
    ({"nombre": None}, True), ({"descripcion": None}, True),
])
def test_strict_noop_and_explicit_none(fields, changed):
    assert role_audit.has_role_changes(role(), RoleUpdate(**fields)) is changed


@pytest.mark.parametrize("fields,before,after", [
    ({"descripcion": None}, {"descripcion": "Description"}, {"descripcion": None}),
    ({"nombre": "New", "descripcion": "Description"}, {"nombre": "ADMIN"}, {"nombre": "New"}),
])
def test_update_diff(monkeypatch, fields, before, after):
    target, operation = role(), Mock()

    def mutate(db, target, update):
        for field in update.model_fields_set:
            setattr(target, field, getattr(update, field))
        return target

    monkeypatch.setattr(crud_roles, "update_role", mutate)
    role_audit.update_role_with_audit(Mock(), operation, target, RoleUpdate(**fields))
    assert operation.success.call_args.kwargs == role_audit.role_event_data(
        "ROL_ACTUALIZADO", 17, before=before, after=after,
    )


def test_create_event(monkeypatch):
    target, operation = role(), Mock()
    monkeypatch.setattr(crud_roles, "create_role", Mock(return_value=target))
    role_audit.create_role_with_audit(Mock(), operation, RoleCreate(nombre="ADMIN"))
    assert operation.success.call_args.kwargs == role_audit.role_event_data(
        "ROL_CREADO", 17, after=role_audit.snapshot_role(target),
    )


def test_delete_event_captured_before_mutation(monkeypatch):
    target, operation = role(), Mock()
    captured = role_audit.role_event_data("ROL_ELIMINADO", 17, before=role_audit.snapshot_role(target))
    monkeypatch.setattr(crud_roles, "delete_role", Mock())
    role_audit.delete_role_with_audit(Mock(), operation, target, captured)
    assert operation.success.call_args.kwargs == captured
    assert captured["valores_posteriores"] is None and "excluded" not in repr(captured)


@pytest.mark.parametrize("mutation", ["create", "update", "delete"])
def test_crud_flush_without_commit_or_rollback(mutation):
    db = Mock()
    if mutation == "create":
        crud_roles.create_role(db, RoleCreate(nombre="New"))
        db.add.assert_called_once()
    elif mutation == "update":
        target = role()
        crud_roles.update_role(db, target, RoleUpdate(descripcion=None))
        assert target.descripcion is None
    else:
        target = role()
        crud_roles.delete_role(db, target)
        db.delete.assert_called_once_with(target)
    db.flush.assert_called_once()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_lock_query_has_no_join_and_targets_role():
    db = Mock()
    crud_roles.get_role_by_id_for_update(db, 17)
    query = db.query.return_value
    query.populate_existing.assert_called_once()
    query.populate_existing.return_value.filter.return_value.with_for_update.assert_called_once_with(of=crud_roles.Rol)
    query.join.assert_not_called()
