import hashlib
from sqlalchemy.orm import Session
from app.models.models import Usuario, Rol
from app.schemas.user import UserCreate, UserUpdate


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_user_by_id(db: Session, user_id: int) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.id_usuario == user_id).first()


def get_user_by_username(db: Session, username: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Usuario]:
    return db.query(Usuario).offset(skip).limit(limit).all()


def role_exists(db: Session, role_id: int) -> bool:
    return db.query(Rol).filter(Rol.id_rol == role_id).first() is not None


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
    update_data = user_in.model_dump(exclude_unset=True)

    if "password" in update_data:
        db_user.password_hash = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, db_user: Usuario) -> None:
    db.delete(db_user)
    db.commit()