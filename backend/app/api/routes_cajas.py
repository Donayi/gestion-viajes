from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.crud.crud_cajas import (
    create_caja,
    delete_caja,
    get_caja_by_id,
    get_caja_by_numero_economico,
    get_caja_by_placas,
    get_cajas,
    update_caja,
)
from app.schemas.caja import (
    CajaCreate,
    CajaResponse,
    CajaUpdate,
)

router = APIRouter(prefix="/cajas", tags=["Cajas"])


@router.post("/", response_model=CajaResponse, status_code=status.HTTP_201_CREATED)
def create_new_caja(caja_in: CajaCreate, db: Session = Depends(get_db)):
    if caja_in.numero_economico is not None:
        existing_numero = get_caja_by_numero_economico(db, caja_in.numero_economico)
        if existing_numero:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una caja con ese número económico",
            )

    existing_placas = get_caja_by_placas(db, caja_in.placas)
    if existing_placas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una caja con esas placas",
        )

    return create_caja(db, caja_in)


@router.get("/", response_model=list[CajaResponse])
def list_cajas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_cajas(db, skip=skip, limit=limit)


@router.get("/{caja_id}", response_model=CajaResponse)
def get_caja(caja_id: int, db: Session = Depends(get_db)):
    db_caja = get_caja_by_id(db, caja_id)
    if not db_caja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja no encontrada",
        )
    return db_caja


@router.put("/{caja_id}", response_model=CajaResponse)
def update_existing_caja(
    caja_id: int,
    caja_in: CajaUpdate,
    db: Session = Depends(get_db),
):
    db_caja = get_caja_by_id(db, caja_id)
    if not db_caja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja no encontrada",
        )

    if caja_in.numero_economico is not None:
        existing_numero = get_caja_by_numero_economico(db, caja_in.numero_economico)
        if existing_numero and existing_numero.id_caja != caja_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otra caja con ese número económico",
            )

    if caja_in.placas is not None:
        existing_placas = get_caja_by_placas(db, caja_in.placas)
        if existing_placas and existing_placas.id_caja != caja_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otra caja con esas placas",
            )

    return update_caja(db, db_caja, caja_in)


@router.delete("/{caja_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_caja(caja_id: int, db: Session = Depends(get_db)):
    db_caja = get_caja_by_id(db, caja_id)
    if not db_caja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja no encontrada",
        )

    delete_caja(db, db_caja)
    return None