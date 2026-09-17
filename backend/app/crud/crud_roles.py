from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.models import Rol
from app.schemas.role import RoleCreate, RoleUpdate


def get_role_by_id(db: Session, role_id: int) -> Rol | None:
    return db.query(Rol).filter(Rol.id_rol == role_id).first()


def get_role_by_name(db: Session, nombre: str) -> Rol | None:
    return db.query(Rol).filter(Rol.nombre == nombre).first()


def get_role_by_id_for_update(db: Session, role_id: int) -> Rol | None:
    return (
        db.query(Rol).populate_existing().filter(Rol.id_rol == role_id)
        .with_for_update(of=Rol).first()
    )


def get_role_referencing_constraints(db: Session) -> frozenset[tuple[str, str, str]]:
    rows = db.execute(text(
        "SELECT n.nspname, r.relname, c.conname FROM pg_catalog.pg_constraint c "
        "JOIN pg_catalog.pg_class r ON r.oid = c.conrelid "
        "JOIN pg_catalog.pg_namespace n ON n.oid = r.relnamespace "
        "JOIN pg_catalog.pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = c.confkey[1] "
        "WHERE c.contype = 'f' AND c.confrelid = 'public.roles'::regclass "
        "AND cardinality(c.confkey) = 1 AND a.attname = 'id_rol'"
    ))
    return frozenset(tuple(row) for row in rows)


def get_roles(db: Session, skip: int = 0, limit: int = 100) -> list[Rol]:
    return db.query(Rol).offset(skip).limit(limit).all()


def create_role(db: Session, role_in: RoleCreate) -> Rol:
    db_role = Rol(
        nombre=role_in.nombre,
        descripcion=role_in.descripcion,
    )
    db.add(db_role)
    db.flush()
    return db_role


def update_role(db: Session, db_role: Rol, role_in: RoleUpdate) -> Rol:
    update_data = role_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_role, field, value)

    db.flush()
    return db_role


def delete_role(db: Session, db_role: Rol) -> None:
    db.delete(db_role)
    db.flush()
