from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.crud.crud_trailers import (
    create_trailer,
    delete_trailer,
    get_trailer_by_id,
    get_trailer_by_numero_economico,
    get_trailer_by_placas,
    get_trailers,
    update_trailer,
)
from app.schemas.trailer import (
    TrailerCreate,
    TrailerResponse,
    TrailerUpdate,
)

router = APIRouter(prefix="/trailers", tags=["Trailers"])


@router.post("/", response_model=TrailerResponse, status_code=status.HTTP_201_CREATED)
def create_new_trailer(trailer_in: TrailerCreate, db: Session = Depends(get_db)):
    existing_numero = get_trailer_by_numero_economico(db, trailer_in.numero_economico)
    if existing_numero:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un trailer con ese número económico",
        )

    existing_placas = get_trailer_by_placas(db, trailer_in.placas)
    if existing_placas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un trailer con esas placas",
        )

    return create_trailer(db, trailer_in)


@router.get("/", response_model=list[TrailerResponse])
def list_trailers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_trailers(db, skip=skip, limit=limit)


@router.get("/{trailer_id}", response_model=TrailerResponse)
def get_trailer(trailer_id: int, db: Session = Depends(get_db)):
    db_trailer = get_trailer_by_id(db, trailer_id)
    if not db_trailer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trailer no encontrado",
        )
    return db_trailer


@router.put("/{trailer_id}", response_model=TrailerResponse)
def update_existing_trailer(
    trailer_id: int,
    trailer_in: TrailerUpdate,
    db: Session = Depends(get_db),
):
    db_trailer = get_trailer_by_id(db, trailer_id)
    if not db_trailer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trailer no encontrado",
        )

    if trailer_in.numero_economico is not None:
        existing_numero = get_trailer_by_numero_economico(db, trailer_in.numero_economico)
        if existing_numero and existing_numero.id_trailer != trailer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro trailer con ese número económico",
            )

    if trailer_in.placas is not None:
        existing_placas = get_trailer_by_placas(db, trailer_in.placas)
        if existing_placas and existing_placas.id_trailer != trailer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro trailer con esas placas",
            )

    return update_trailer(db, db_trailer, trailer_in)


@router.delete("/{trailer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_trailer(trailer_id: int, db: Session = Depends(get_db)):
    db_trailer = get_trailer_by_id(db, trailer_id)
    if not db_trailer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trailer no encontrado",
        )

    delete_trailer(db, db_trailer)
    return None