from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.crud.crud_clientes import (
    create_cliente,
    delete_cliente,
    get_cliente_by_id,
    get_clientes,
    update_cliente,
)
from app.schemas.cliente import (
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def create_new_cliente(cliente_in: ClienteCreate, db: Session = Depends(get_db)):
    return create_cliente(db, cliente_in)


@router.get("/", response_model=list[ClienteResponse])
def list_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_clientes(db, skip=skip, limit=limit)


@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(cliente_id: int, db: Session = Depends(get_db)):
    db_cliente = get_cliente_by_id(db, cliente_id)
    if not db_cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return db_cliente


@router.put("/{cliente_id}", response_model=ClienteResponse)
def update_existing_cliente(
    cliente_id: int,
    cliente_in: ClienteUpdate,
    db: Session = Depends(get_db),
):
    db_cliente = get_cliente_by_id(db, cliente_id)
    if not db_cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    return update_cliente(db, db_cliente, cliente_in)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_cliente(cliente_id: int, db: Session = Depends(get_db)):
    db_cliente = get_cliente_by_id(db, cliente_id)
    if not db_cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    delete_cliente(db, db_cliente)
    return None