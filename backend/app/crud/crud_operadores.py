from sqlalchemy.orm import Session
from app.models.models import Operador, Usuario
from app.schemas.operador import OperadorCreate, OperadorUpdate


def get_operador_by_id(db: Session, operador_id: int) -> Operador | None:
    return db.query(Operador).filter(Operador.id_operador == operador_id).first()


def get_operador_by_usuario_id(db: Session, usuario_id: int) -> Operador | None:
    return db.query(Operador).filter(Operador.id_usuario == usuario_id).first()


def get_operadores(db: Session, skip: int = 0, limit: int = 100) -> list[Operador]:
    return db.query(Operador).offset(skip).limit(limit).all()


def user_exists(db: Session, usuario_id: int) -> bool:
    return db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first() is not None


def create_operador(db: Session, operador_in: OperadorCreate) -> Operador:
    db_operador = Operador(
        id_usuario=operador_in.id_usuario,
        alias=operador_in.alias,
        numero_licencia=operador_in.numero_licencia,
        licencia_vigencia=operador_in.licencia_vigencia,
        sua=operador_in.sua,
        sua_vigencia=operador_in.sua_vigencia,
        estudio_medico=operador_in.estudio_medico,
        activo=operador_in.activo,
    )
    db.add(db_operador)
    db.commit()
    db.refresh(db_operador)
    return db_operador


def update_operador(db: Session, db_operador: Operador, operador_in: OperadorUpdate) -> Operador:
    update_data = operador_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_operador, field, value)

    db.commit()
    db.refresh(db_operador)
    return db_operador


def delete_operador(db: Session, db_operador: Operador) -> None:
    db.delete(db_operador)
    db.commit()