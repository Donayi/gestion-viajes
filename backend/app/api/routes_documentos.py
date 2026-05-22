from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps_auth import require_admin
from app.crud.crud_viajes import (
    archivo_storage_exists,
    caja_exists,
    get_tipos_documento,
    operador_exists,
    tipo_documento_exists,
    trailer_exists,
)
from app.db.deps import get_db
from app.models.models import Documento, Usuario
from app.schemas.documento import (
    DocumentoAdminCreate,
    DocumentoAdminResponse,
    DocumentoAdminUpdate,
    TipoDocumentoResponse,
)


router = APIRouter(prefix="/documentos", tags=["Documentos"])


def _validar_entidad_documental(db: Session, entidad_tipo: str, entidad_id: int) -> None:
    existe = {
        "OPERADOR": operador_exists,
        "TRAILER": trailer_exists,
        "CAJA": caja_exists,
    }.get(entidad_tipo)

    if existe is None or not existe(db, entidad_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La entidad especificada no existe para asociar documentos",
        )


def _aplicar_filtro_entidad(query, entidad_tipo: str, entidad_id: int):
    if entidad_tipo == "OPERADOR":
        return query.filter(Documento.id_operador == entidad_id)
    if entidad_tipo == "TRAILER":
        return query.filter(Documento.id_trailer == entidad_id)
    if entidad_tipo == "CAJA":
        return query.filter(Documento.id_caja == entidad_id)
    return query.filter(False)


def _build_documento_base_query(db: Session):
    return db.query(Documento).options(
        joinedload(Documento.tipo_documento),
        joinedload(Documento.archivo),
    )


@router.get("/tipos", response_model=list[TipoDocumentoResponse])
def list_tipos_documento_admin(
    aplica_a: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    tipos = get_tipos_documento(db)
    if aplica_a:
        return [tipo for tipo in tipos if tipo.aplica_a == aplica_a]
    return tipos


@router.get("", response_model=list[DocumentoAdminResponse])
def list_documentos_admin(
    entidad_tipo: str | None = Query(default=None),
    entidad_id: int | None = Query(default=None),
    solo_activos: bool = Query(default=False),
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    query = _build_documento_base_query(db).filter(Documento.id_viaje.is_(None))

    if entidad_tipo and entidad_id is not None:
        _validar_entidad_documental(db, entidad_tipo, entidad_id)
        query = _aplicar_filtro_entidad(query, entidad_tipo, entidad_id)

    if solo_activos:
        query = query.filter(Documento.activo.is_(True))

    return query.order_by(Documento.id_documento.desc()).all()


@router.post("", response_model=DocumentoAdminResponse, status_code=status.HTTP_201_CREATED)
def create_documento_admin(
    documento_in: DocumentoAdminCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    _validar_entidad_documental(db, documento_in.entidad_tipo, documento_in.entidad_id)

    if not tipo_documento_exists(db, documento_in.id_tipo_documento):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de documento especificado no existe",
        )

    if not archivo_storage_exists(db, documento_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    documento_data = {
        "id_tipo_documento": documento_in.id_tipo_documento,
        "id_archivo": documento_in.id_archivo,
        "fecha_expiracion": documento_in.fecha_vencimiento,
        "comentario": documento_in.comentario,
        "activo": documento_in.activo,
        "estatus": "VIGENTE" if documento_in.activo else "INACTIVO",
        "subido_por": current_user.id_usuario,
    }

    if documento_in.entidad_tipo == "OPERADOR":
        documento_data["id_operador"] = documento_in.entidad_id
    elif documento_in.entidad_tipo == "TRAILER":
        documento_data["id_trailer"] = documento_in.entidad_id
    elif documento_in.entidad_tipo == "CAJA":
        documento_data["id_caja"] = documento_in.entidad_id

    db_documento = Documento(**documento_data)
    db.add(db_documento)
    db.commit()
    db.refresh(db_documento)
    return db_documento


@router.put("/{documento_id}", response_model=DocumentoAdminResponse)
def update_documento_admin(
    documento_id: int,
    documento_in: DocumentoAdminUpdate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    db_documento = _build_documento_base_query(db).filter(Documento.id_documento == documento_id).first()
    if not db_documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado",
        )

    if documento_in.id_tipo_documento is not None and not tipo_documento_exists(db, documento_in.id_tipo_documento):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de documento especificado no existe",
        )

    if documento_in.id_archivo is not None and not archivo_storage_exists(db, documento_in.id_archivo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo especificado no existe",
        )

    update_data = documento_in.model_dump(exclude_unset=True)

    if "fecha_vencimiento" in update_data:
        update_data["fecha_expiracion"] = update_data.pop("fecha_vencimiento")

    if "activo" in update_data:
        update_data["estatus"] = "VIGENTE" if update_data["activo"] else "INACTIVO"

    for field, value in update_data.items():
        setattr(db_documento, field, value)

    db.commit()
    db.refresh(db_documento)
    return db_documento


@router.delete("/{documento_id}", response_model=DocumentoAdminResponse)
def deactivate_documento_admin(
    documento_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    db_documento = _build_documento_base_query(db).filter(Documento.id_documento == documento_id).first()
    if not db_documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado",
        )

    db_documento.activo = False
    db_documento.estatus = "INACTIVO"
    db.commit()
    db.refresh(db_documento)
    return db_documento
