from sqlalchemy.orm import Session
from app.models.models import Caja
from app.schemas.caja import CajaCreate, CajaUpdate


def get_caja_by_id(db: Session, caja_id: int) -> Caja | None:
    return db.query(Caja).filter(Caja.id_caja == caja_id).first()


def get_caja_by_numero_economico(db: Session, numero_economico: str) -> Caja | None:
    return db.query(Caja).filter(Caja.numero_economico == numero_economico).first()


def get_caja_by_placas(db: Session, placas: str) -> Caja | None:
    return db.query(Caja).filter(Caja.placas == placas).first()


def get_cajas(db: Session, skip: int = 0, limit: int = 100) -> list[Caja]:
    return db.query(Caja).offset(skip).limit(limit).all()


def create_caja(db: Session, caja_in: CajaCreate) -> Caja:
    db_caja = Caja(
        numero_economico=caja_in.numero_economico,
        placas=caja_in.placas,
        tipo_caja=caja_in.tipo_caja,
        marca=caja_in.marca,
        modelo=caja_in.modelo,
        anio=caja_in.anio,
        poliza_seguro=caja_in.poliza_seguro,
        seguro_vigencia=caja_in.seguro_vigencia,
        tarjeta_circulacion=caja_in.tarjeta_circulacion,
        tarjeta_vigencia=caja_in.tarjeta_vigencia,
        verificacion=caja_in.verificacion,
        verificacion_vigencia=caja_in.verificacion_vigencia,
        activo=caja_in.activo,
    )
    db.add(db_caja)
    db.commit()
    db.refresh(db_caja)
    return db_caja


def update_caja(db: Session, db_caja: Caja, caja_in: CajaUpdate) -> Caja:
    update_data = caja_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_caja, field, value)

    db.commit()
    db.refresh(db_caja)
    return db_caja


def delete_caja(db: Session, db_caja: Caja) -> None:
    db.delete(db_caja)
    db.commit()