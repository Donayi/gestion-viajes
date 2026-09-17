"""Administrative-user payloads only; transaction ownership stays in the route."""

from app.crud import crud_usuarios


AUDIT_FIELDS = ("username", "nombre", "apellido", "activo", "id_rol")
PRIVATE_FIELDS = ("telefono", "fecha_nacimiento")
FUNCTIONAL_FIELDS = AUDIT_FIELDS + PRIVATE_FIELDS


def snapshot_user(user):
    return {
        "username": user.username, "nombre": user.nombre, "apellido": user.apellido,
        "activo": user.activo, "id_rol": int(user.id_rol),
    }


def has_user_changes(user, update):
    return any(
        getattr(user, field) != getattr(update, field)
        for field in FUNCTIONAL_FIELDS if field in update.model_fields_set
    )


def diff_user_snapshots(before, after):
    changed = [field for field in AUDIT_FIELDS if before[field] != after[field]]
    return ({field: before[field] for field in changed}, {field: after[field] for field in changed})


def user_event_data(action, user_id, *, before=None, after=None, data=None):
    return {
        "categoria": "SEGURIDAD", "modulo": "USUARIOS", "accion": action,
        "entidad_tipo": "USUARIO", "entidad_id": str(user_id),
        "valores_anteriores": before, "valores_posteriores": after, "datos_evento": data,
    }


def create_user_with_audit(db, operation, user_in):
    user = crud_usuarios.create_user(db, user_in)
    operation.success(**user_event_data("USUARIO_CREADO", user.id_usuario, after=snapshot_user(user)))
    return user


def update_user_with_audit(db, operation, user, update):
    # The route resolves no-op BEFORE opening the required coordinator.
    before = snapshot_user(user)
    private_changed = any(
        getattr(user, field) != getattr(update, field)
        for field in PRIVATE_FIELDS if field in update.model_fields_set
    )
    user = crud_usuarios.update_user_admin(db, user, update)
    previous, following = diff_user_snapshots(before, snapshot_user(user))
    operation.success(**user_event_data(
        "USUARIO_ACTUALIZADO", user.id_usuario, before=previous, after=following,
        data={"otros_datos_actualizados": True} if private_changed else None,
    ))
    return user


def change_user_password_with_audit(db, operation, user, password_in):
    crud_usuarios.update_user_password(db, user, password_in)
    operation.success(**user_event_data(
        "USUARIO_CREDENCIAL_CAMBIADA", user.id_usuario, data={"credencial_cambiada": True},
    ))


def delete_user_with_audit(db, operation, user, event_data):
    # Captured by the route before deletion, also usable after rollback.
    crud_usuarios.delete_user(db, user)
    operation.success(**event_data)
