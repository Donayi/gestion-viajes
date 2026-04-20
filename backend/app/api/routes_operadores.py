from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.crud.crud_operadores import (
    create_operador,
    delete_operador,
    get_operador_by_id,
    get_operador_by_usuario_id,
    get_operadores,
    update_operador,
    user_exists,
)
from app.schemas.operador import (
    OperadorCreate,
    OperadorResponse,
    OperadorUpdate,
)

router = APIRouter(prefix="/operadores", tags=["Operadores"])


@router.post("/", response_model=OperadorResponse, status_code=status.HTTP_201_CREATED)
def create_new_operador(operador_in: OperadorCreate, db: Session = Depends(get_db)):
    if not user_exists(db, operador_in.id_usuario):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario especificado no existe",
        )

    existing_operador = get_operador_by_usuario_id(db, operador_in.id_usuario)
    if existing_operador:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese usuario ya está asociado a un operador",
        )

    return create_operador(db, operador_in)


@router.get("/", response_model=list[OperadorResponse])
def list_operadores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_operadores(db, skip=skip, limit=limit)


@router.get("/{operador_id}", response_model=OperadorResponse)
def get_operador(operador_id: int, db: Session = Depends(get_db)):
    db_operador = get_operador_by_id(db, operador_id)
    if not db_operador:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operador no encontrado",
        )
    return db_operador


@router.put("/{operador_id}", response_model=OperadorResponse)
def update_existing_operador(
    operador_id: int,
    operador_in: OperadorUpdate,
    db: Session = Depends(get_db),
):
    db_operador = get_operador_by_id(db, operador_id)
    if not db_operador:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operador no encontrado",
        )

    if operador_in.id_usuario is not None:
        if not user_exists(db, operador_in.id_usuario):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario especificado no existe",
            )

        existing_operador = get_operador_by_usuario_id(db, operador_in.id_usuario)
        if existing_operador and existing_operador.id_operador != operador_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ese usuario ya está asociado a otro operador",
            )

    return update_operador(db, db_operador, operador_in)


@router.delete("/{operador_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_operador(operador_id: int, db: Session = Depends(get_db)):
    db_operador = get_operador_by_id(db, operador_id)
    if not db_operador:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operador no encontrado",
        )

    delete_operador(db, db_operador)
    return None