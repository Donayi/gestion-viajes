from pydantic import SecretStr
from sqlalchemy.orm import Session, joinedload
from app.models.models import Usuario, Rol
from app.core.security import get_password_hash, verify_password
from app.schemas.auth import BootstrapAdminCreate
from app.schemas.user import UserCreate, UserUpdate


def hash_password(password: str | SecretStr) -> str:
    return get_password_hash(password)


def get_user_by_id(db: Session, user_id: int) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.id_usuario == user_id).first()


def get_user_by_username(db: Session, username: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.username == username).first()


def get_role_by_name(db: Session, role_name: str) -> Rol | None:
    return db.query(Rol).filter(Rol.nombre == role_name).first()


def get_user_with_role_and_operador(db: Session, user_id: int) -> Usuario | None:
    return (
        db.query(Usuario)
        .options(
            joinedload(Usuario.rol),
            joinedload(Usuario.operador),
        )
        .filter(Usuario.id_usuario == user_id)
        .first()
    )


def get_user_by_username_with_role_and_operador(db: Session, username: str) -> Usuario | None:
    return (
        db.query(Usuario)
        .options(
            joinedload(Usuario.rol),
            joinedload(Usuario.operador),
        )
        .filter(Usuario.username == username)
        .first()
    )


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Usuario]:
    return db.query(Usuario).offset(skip).limit(limit).all()


def role_exists(db: Session, role_id: int) -> bool:
    return db.query(Rol).filter(Rol.id_rol == role_id).first() is not None


def admin_exists(db: Session) -> bool:
    return (
        db.query(Usuario)
        .join(Rol, Usuario.id_rol == Rol.id_rol)
        .filter(Rol.nombre == "ADMIN")
        .first()
        is not None
    )


def get_or_create_admin_role(db: Session) -> Rol:
    role = get_role_by_name(db, "ADMIN")
    if role is not None:
        return role

    role = Rol(
        nombre="ADMIN",
        descripcion="Administrador del sistema",
    )
    db.add(role)
    db.flush()
    return role


def authenticate_user(db: Session, username: str, password: str) -> Usuario | None:
    user = get_user_by_username_with_role_and_operador(db, username)
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.activo:
        return None

    return user


def create_bootstrap_admin(db: Session, bootstrap_in: BootstrapAdminCreate) -> Usuario:
    if admin_exists(db):
        raise ValueError(
            "Ya existe un usuario administrador. El bootstrap inicial ya no esta disponible"
        )

    if get_user_by_username(db, bootstrap_in.username):
        raise ValueError("Ya existe un usuario con ese username")

    admin_role = get_or_create_admin_role(db)

    db_user = Usuario(
        username=bootstrap_in.username,
        password_hash=hash_password(bootstrap_in.password),
        nombre=bootstrap_in.nombre,
        apellido=bootstrap_in.apellido,
        fecha_nacimiento=bootstrap_in.fecha_nacimiento,
        telefono=bootstrap_in.telefono,
        activo=True,
        id_rol=admin_role.id_rol,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.refresh(admin_role)
    return db_user


def create_user(db: Session, user_in: UserCreate) -> Usuario:
    db_user = Usuario(
        username=user_in.username,
        password_hash=hash_password(user_in.password),
        nombre=user_in.nombre,
        apellido=user_in.apellido,
        fecha_nacimiento=user_in.fecha_nacimiento,
        telefono=user_in.telefono,
        activo=user_in.activo,
        id_rol=user_in.id_rol,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, db_user: Usuario, user_in: UserUpdate) -> Usuario:
    update_data = user_in.model_dump(exclude_unset=True, exclude={"password"})

    if user_in.password is not None:
        db_user.password_hash = hash_password(user_in.password)

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, db_user: Usuario) -> None:
    db.delete(db_user)
    db.commit()
