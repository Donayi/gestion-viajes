from sqlalchemy.orm import Session
from app.models.models import Cliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate


def get_cliente_by_id(db: Session, cliente_id: int) -> Cliente | None:
    return db.query(Cliente).filter(Cliente.id_cliente == cliente_id).first()


def get_clientes(db: Session, skip: int = 0, limit: int = 100) -> list[Cliente]:
    return db.query(Cliente).offset(skip).limit(limit).all()


def create_cliente(db: Session, cliente_in: ClienteCreate) -> Cliente:
    db_cliente = Cliente(
        nombre_razon_social=cliente_in.nombre_razon_social,
        rfc=cliente_in.rfc,
        direccion=cliente_in.direccion,
        cp=cliente_in.cp,
        regimen_fiscal=cliente_in.regimen_fiscal,
        tiempo_credito=cliente_in.tiempo_credito,
        contacto_nombre=cliente_in.contacto_nombre,
        contacto_telefono=cliente_in.contacto_telefono,
        contacto_email=cliente_in.contacto_email,
        activo=cliente_in.activo,
    )
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


def update_cliente(db: Session, db_cliente: Cliente, cliente_in: ClienteUpdate) -> Cliente:
    update_data = cliente_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_cliente, field, value)

    db.commit()
    db.refresh(db_cliente)
    return db_cliente


def delete_cliente(db: Session, db_cliente: Cliente) -> None:
    db.delete(db_cliente)
    db.commit()