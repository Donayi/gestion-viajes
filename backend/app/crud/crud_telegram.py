from sqlalchemy.orm import Session

from app.models.models import TelegramDestinatario
from app.schemas.telegram import TelegramDestinatarioCreate, TelegramDestinatarioUpdate


def get_destinatarios(db: Session, solo_activos: bool = False) -> list[TelegramDestinatario]:
    query = db.query(TelegramDestinatario)
    if solo_activos:
        query = query.filter(TelegramDestinatario.activo.is_(True))
    return query.order_by(TelegramDestinatario.nombre.asc(), TelegramDestinatario.id_destinatario.asc()).all()


def get_destinatario_by_id(db: Session, destinatario_id: int) -> TelegramDestinatario | None:
    return (
        db.query(TelegramDestinatario)
        .filter(TelegramDestinatario.id_destinatario == destinatario_id)
        .first()
    )


def create_destinatario(
    db: Session,
    destinatario_in: TelegramDestinatarioCreate,
) -> TelegramDestinatario:
    db_destinatario = TelegramDestinatario(**destinatario_in.model_dump())
    db.add(db_destinatario)
    db.commit()
    db.refresh(db_destinatario)
    return db_destinatario


def update_destinatario(
    db: Session,
    db_destinatario: TelegramDestinatario,
    destinatario_in: TelegramDestinatarioUpdate,
) -> TelegramDestinatario:
    for field, value in destinatario_in.model_dump(exclude_unset=True).items():
        setattr(db_destinatario, field, value)
    db.commit()
    db.refresh(db_destinatario)
    return db_destinatario


def soft_delete_destinatario(
    db: Session,
    db_destinatario: TelegramDestinatario,
) -> TelegramDestinatario:
    db_destinatario.activo = False
    db.commit()
    db.refresh(db_destinatario)
    return db_destinatario
