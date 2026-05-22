from sqlalchemy.orm import Session

from app.models.models import Rol


BASE_ROLES = (
    ("ADMIN", "Administrador del sistema"),
    ("OPERADOR", "Operador de viajes"),
    ("MANTENIMIENTO", "Personal responsable de mantenimiento"),
)


def run_seed_roles(db: Session) -> None:
    for nombre, descripcion in BASE_ROLES:
        exists = db.query(Rol).filter(Rol.nombre == nombre).first()
        if exists is None:
            db.add(Rol(nombre=nombre, descripcion=descripcion))
    db.commit()
