from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.crud.crud_telegram import (
    create_destinatario,
    get_destinatario_by_id,
    get_destinatarios,
    soft_delete_destinatario,
    update_destinatario,
)
from app.db.deps import get_db
from app.models.models import Usuario
from app.schemas.telegram import (
    TelegramDestinatarioCreate,
    TelegramDestinatarioResponse,
    TelegramDestinatarioUpdate,
    TelegramTestResponse,
)
from app.services.telegram_service import send_telegram_message


router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.get("/destinatarios", response_model=list[TelegramDestinatarioResponse])
def list_telegram_destinatarios(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    return get_destinatarios(db)


@router.post("/destinatarios", response_model=TelegramDestinatarioResponse, status_code=status.HTTP_201_CREATED)
def create_telegram_destinatario(
    destinatario_in: TelegramDestinatarioCreate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    existing = next(
        (row for row in get_destinatarios(db) if row.chat_id == destinatario_in.chat_id.strip()),
        None,
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El chat_id ya existe")
    payload = destinatario_in.model_copy(update={"chat_id": destinatario_in.chat_id.strip(), "nombre": destinatario_in.nombre.strip()})
    return create_destinatario(db, payload)


@router.put("/destinatarios/{destinatario_id}", response_model=TelegramDestinatarioResponse)
def update_telegram_destinatario(
    destinatario_id: int,
    destinatario_in: TelegramDestinatarioUpdate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    db_destinatario = get_destinatario_by_id(db, destinatario_id)
    if not db_destinatario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destinatario no encontrado")

    if destinatario_in.chat_id:
        existing = next(
            (
                row
                for row in get_destinatarios(db)
                if row.chat_id == destinatario_in.chat_id.strip() and row.id_destinatario != destinatario_id
            ),
            None,
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El chat_id ya existe")

    normalized = destinatario_in.model_dump(exclude_unset=True)
    if "chat_id" in normalized and normalized["chat_id"] is not None:
        normalized["chat_id"] = normalized["chat_id"].strip()
    if "nombre" in normalized and normalized["nombre"] is not None:
        normalized["nombre"] = normalized["nombre"].strip()
    return update_destinatario(db, db_destinatario, TelegramDestinatarioUpdate(**normalized))


@router.delete("/destinatarios/{destinatario_id}", response_model=TelegramDestinatarioResponse)
def delete_telegram_destinatario(
    destinatario_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    db_destinatario = get_destinatario_by_id(db, destinatario_id)
    if not db_destinatario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destinatario no encontrado")
    return soft_delete_destinatario(db, db_destinatario)


@router.post("/test/{destinatario_id}", response_model=TelegramTestResponse)
def send_test_telegram_message(
    destinatario_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    db_destinatario = get_destinatario_by_id(db, destinatario_id)
    if not db_destinatario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destinatario no encontrado")

    enviado = send_telegram_message(
        f"✅ Prueba de notificaciones DAFREQ para {db_destinatario.nombre}.",
        chat_id=db_destinatario.chat_id,
    )
    return TelegramTestResponse(
        enviado=enviado,
        mensaje="Mensaje de prueba enviado" if enviado else "No fue posible enviar el mensaje de prueba",
        destinatario=db_destinatario,
    )
