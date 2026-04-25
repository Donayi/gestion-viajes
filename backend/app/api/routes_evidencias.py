from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin_or_operador
from app.core.storage_r2 import build_evidencia_file_key, generate_presigned_upload_url
from app.crud.crud_viajes import create_archivo_storage_upload
from app.db.deps import get_db
from app.models.models import Usuario
from app.schemas.evidencia import PresignUploadRequest, PresignUploadResponse


router = APIRouter(prefix="/evidencias", tags=["Evidencias"])


@router.post(
    "/presign-upload",
    response_model=PresignUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def presign_upload_evidencia(
    upload_in: PresignUploadRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin_or_operador),
):
    try:
        file_key = build_evidencia_file_key(upload_in.filename)
        upload_url = generate_presigned_upload_url(file_key, upload_in.content_type)
        extension = Path(upload_in.filename).suffix.lower() or None
        db_archivo = create_archivo_storage_upload(
            db=db,
            file_key=file_key,
            nombre_original=upload_in.filename,
            extension=extension,
            content_type=upload_in.content_type,
            size_bytes=upload_in.size_bytes,
            subido_por=current_user.id_usuario,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible generar la subida para evidencia",
        ) from exc

    return PresignUploadResponse(
        upload_url=upload_url,
        file_key=file_key,
        id_archivo=db_archivo.id_archivo,
    )
