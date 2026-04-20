from sqlalchemy.orm import Session
from app.models.models import Trailer
from app.schemas.trailer import TrailerCreate, TrailerUpdate


def get_trailer_by_id(db: Session, trailer_id: int) -> Trailer | None:
    return db.query(Trailer).filter(Trailer.id_trailer == trailer_id).first()


def get_trailer_by_numero_economico(db: Session, numero_economico: str) -> Trailer | None:
    return db.query(Trailer).filter(Trailer.numero_economico == numero_economico).first()


def get_trailer_by_placas(db: Session, placas: str) -> Trailer | None:
    return db.query(Trailer).filter(Trailer.placas == placas).first()


def get_trailers(db: Session, skip: int = 0, limit: int = 100) -> list[Trailer]:
    return db.query(Trailer).offset(skip).limit(limit).all()


def create_trailer(db: Session, trailer_in: TrailerCreate) -> Trailer:
    db_trailer = Trailer(
        numero_economico=trailer_in.numero_economico,
        placas=trailer_in.placas,
        marca=trailer_in.marca,
        modelo=trailer_in.modelo,
        anio=trailer_in.anio,
        poliza_seguro=trailer_in.poliza_seguro,
        seguro_vigencia=trailer_in.seguro_vigencia,
        tarjeta_circulacion=trailer_in.tarjeta_circulacion,
        tarjeta_vigencia=trailer_in.tarjeta_vigencia,
        verificacion=trailer_in.verificacion,
        verificacion_vigencia=trailer_in.verificacion_vigencia,
        activo=trailer_in.activo,
    )
    db.add(db_trailer)
    db.commit()
    db.refresh(db_trailer)
    return db_trailer


def update_trailer(db: Session, db_trailer: Trailer, trailer_in: TrailerUpdate) -> Trailer:
    update_data = trailer_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_trailer, field, value)

    db.commit()
    db.refresh(db_trailer)
    return db_trailer


def delete_trailer(db: Session, db_trailer: Trailer) -> None:
    db.delete(db_trailer)
    db.commit()