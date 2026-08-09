from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.core.config import settings
from app.crud.crud_respaldos import get_respaldo_by_id, list_respaldos
from app.db.deps import get_db
from app.models.models import RespaldoControl, Usuario
from app.schemas.respaldo import (
    ListaRespaldosAdministrativos,
    RespaldoAdministrativo,
    SolicitudRespaldoManual,
)
from app.services.backup_runtime import (
    BACKUP_ALREADY_RUNNING,
    BACKUP_DISABLED,
    BackupRuntimeError,
    run_backup,
)
from app.services.backup_package import is_safe_backup_filename
from app.services.backup_service import BackupGenerationError


router = APIRouter(prefix="/respaldos", tags=["respaldos"])


def _response(record: RespaldoControl) -> RespaldoAdministrativo:
    return RespaldoAdministrativo(
        id_respaldo=record.id_respaldo,
        nombre_archivo=record.nombre_archivo,
        origen=record.origen,
        estado=record.estado,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
        table_count=record.table_count,
        row_count=record.row_count,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        error_mensaje=record.error_detalle,
    )


@router.post("/manual", response_model=RespaldoAdministrativo)
def generate_manual_backup(
    _request: SolicitudRespaldoManual,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> RespaldoAdministrativo:
    try:
        result = run_backup(
            db,
            trigger="MANUAL",
            application_version=settings.app_version,
            actor_source="USER",
            actor_original_id=str(current_user.id_usuario),
            actor_username_snapshot=current_user.username,
            actor_role_snapshot=current_user.rol.nombre,
            actor_nombre_snapshot=f"{current_user.nombre} {current_user.apellido}".strip(),
        )
    except BackupRuntimeError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code == BACKUP_ALREADY_RUNNING
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        if exc.code not in {BACKUP_ALREADY_RUNNING, BACKUP_DISABLED}:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=exc.public_message) from None
    except BackupGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.public_message,
        ) from None
    record = get_respaldo_by_id(db, result.backup_id)
    if record is None:
        raise HTTPException(status_code=500, detail="No fue posible consultar el respaldo generado")
    return _response(record)


@router.get("", response_model=ListaRespaldosAdministrativos)
def get_backup_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
) -> ListaRespaldosAdministrativos:
    items, total = list_respaldos(db, page=page, page_size=page_size)
    return ListaRespaldosAdministrativos(
        items=[_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def _open_download(record: RespaldoControl) -> tuple[int, int]:
    if record.estado != "DISPONIBLE" or not record.sha256 or record.size_bytes is None:
        raise HTTPException(status_code=409, detail="El respaldo no esta disponible")
    relative = Path(record.ruta_relativa)
    if (
        relative.is_absolute()
        or relative.name != record.ruta_relativa
        or relative.name != record.nombre_archivo
        or not is_safe_backup_filename(record.nombre_archivo)
    ):
        raise HTTPException(status_code=409, detail="La ubicacion del respaldo no es valida")
    root = Path(settings.backup_storage_dir)
    try:
        if root.is_symlink():
            raise OSError
        resolved_root = root.resolve(strict=True)
        root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        root_fd = os.open(resolved_root, root_flags)
        try:
            file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            file_fd = os.open(relative.name, file_flags, dir_fd=root_fd)
        finally:
            os.close(root_fd)
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != record.size_bytes:
            os.close(file_fd)
            raise HTTPException(status_code=409, detail="El archivo de respaldo no es valido")
        digest = hashlib.sha256()
        while chunk := os.read(file_fd, settings.backup_stream_chunk_bytes):
            digest.update(chunk)
        if digest.hexdigest() != record.sha256:
            os.close(file_fd)
            raise HTTPException(status_code=409, detail="La integridad del respaldo no coincide")
        os.lseek(file_fd, 0, os.SEEK_SET)
        return file_fd, metadata.st_size
    except HTTPException:
        raise
    except OSError:
        raise HTTPException(status_code=404, detail="El archivo de respaldo no existe") from None


def _stream_file(file_fd: int) -> Iterator[bytes]:
    try:
        while chunk := os.read(file_fd, settings.backup_stream_chunk_bytes):
            yield chunk
    finally:
        os.close(file_fd)


@router.get("/{respaldo_id}/descarga")
def download_backup(
    respaldo_id: UUID,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
) -> StreamingResponse:
    record = get_respaldo_by_id(db, respaldo_id)
    if record is None:
        raise HTTPException(status_code=404, detail="El respaldo no existe")
    file_fd, file_size = _open_download(record)
    return StreamingResponse(
        _stream_file(file_fd),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{record.nombre_archivo}"',
            "Content-Length": str(file_size),
            "X-Content-Type-Options": "nosniff",
        },
    )
