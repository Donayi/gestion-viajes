from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.crud import crud_usuarios
from app.schemas.user import UserAdminUpdate, UserCreate, UserPasswordUpdate
from app.services import user_audit


def user():
    return SimpleNamespace(
        id_usuario=17, username="target", nombre="Name", apellido="Surname", activo=True,
        id_rol=2, telefono="private-phone", fecha_nacimiento=None, password_hash="private-hash",
    )


def test_snapshot_exact_allowlist():
    assert user_audit.snapshot_user(user()) == {
        "username": "target", "nombre": "Name", "apellido": "Surname", "activo": True, "id_rol": 2,
    }


@pytest.mark.parametrize("update,changed", [
    ({}, False), ({"activo": True}, False), ({"telefono": "private-phone"}, False),
    ({"telefono": None}, True), ({"fecha_nacimiento": "2000-01-01"}, True),
    ({"activo": False}, True), ({"nombre": None}, True),
])
def test_functional_change_detection(update, changed):
    assert user_audit.has_user_changes(user(), UserAdminUpdate(**update)) is changed


def test_diff_contains_only_changed_approved_fields():
    before = user_audit.snapshot_user(user())
    after = dict(before, activo=False, id_rol=3)
    assert user_audit.diff_user_snapshots(before, after) == (
        {"activo": True, "id_rol": 2}, {"activo": False, "id_rol": 3},
    )


@pytest.mark.parametrize("private_only", [True, False])
def test_update_private_indicator_without_values(monkeypatch, private_only):
    target, operation = user(), Mock()

    def mutate(db, target, update):
        for field in update.model_fields_set:
            setattr(target, field, getattr(update, field))
        return target

    monkeypatch.setattr(crud_usuarios, "update_user_admin", mutate)
    fields = {"telefono": "new-private-phone"}
    if not private_only:
        fields["nombre"] = "New Name"
    user_audit.update_user_with_audit(Mock(), operation, target, UserAdminUpdate(**fields))
    event = operation.success.call_args.kwargs
    assert event["accion"] == "USUARIO_ACTUALIZADO"
    assert event["datos_evento"] == {"otros_datos_actualizados": True}
    assert event["valores_anteriores"] == ({} if private_only else {"nombre": "Name"})
    assert event["valores_posteriores"] == ({} if private_only else {"nombre": "New Name"})
    assert "phone" not in repr(event)


def test_password_exact_event(monkeypatch):
    mutation, operation = Mock(), Mock()
    monkeypatch.setattr(crud_usuarios, "update_user_password", mutation)
    user_audit.change_user_password_with_audit(Mock(), operation, user(), UserPasswordUpdate(new_password="secret-password"))
    payload = operation.success.call_args.kwargs
    assert payload == user_audit.user_event_data(
        "USUARIO_CREDENCIAL_CAMBIADA", 17, data={"credencial_cambiada": True},
    )
    assert "secret-password" not in repr(payload) and "private-hash" not in repr(payload)


def test_create_and_delete_snapshots(monkeypatch):
    target, operation = user(), Mock()
    monkeypatch.setattr(crud_usuarios, "create_user", Mock(return_value=target))
    monkeypatch.setattr(crud_usuarios, "delete_user", Mock())
    user_audit.create_user_with_audit(Mock(), operation, Mock())
    assert operation.success.call_args.kwargs == user_audit.user_event_data(
        "USUARIO_CREADO", 17, after=user_audit.snapshot_user(target),
    )
    deletion = user_audit.user_event_data("USUARIO_ELIMINADO", 17, before=user_audit.snapshot_user(target))
    user_audit.delete_user_with_audit(Mock(), operation, target, deletion)
    assert operation.success.call_args.kwargs == deletion


@pytest.mark.parametrize("operation", ["create", "update", "password", "delete"])
def test_real_crud_flush_without_commit_or_rollback(monkeypatch, operation):
    db, target = Mock(), user()
    monkeypatch.setattr(crud_usuarios, "hash_password", Mock(return_value="functional-hash"))
    if operation == "create":
        crud_usuarios.create_user(db, UserCreate(
            username="target", nombre="Name", apellido="Surname", id_rol=2, password="secret-password",
        ))
        db.add.assert_called_once()
    elif operation == "update":
        crud_usuarios.update_user_admin(db, target, UserAdminUpdate(activo=False))
        assert target.activo is False
    elif operation == "password":
        crud_usuarios.update_user_password(db, target, UserPasswordUpdate(new_password="secret-password"))
        assert target.password_hash == "functional-hash"
    else:
        crud_usuarios.delete_user(db, target)
        db.delete.assert_called_once_with(target)
    db.flush.assert_called_once()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_lock_query_is_targeted():
    db = Mock()
    crud_usuarios.get_user_by_id_for_update(db, 17)
    query = db.query.return_value
    query.populate_existing.assert_called_once()
    query.populate_existing.return_value.filter.return_value.with_for_update.assert_called_once_with(of=crud_usuarios.Usuario)
