from sqlalchemy.orm import Session

from app.models.models import TipoDocumento


TIPOS_DOCUMENTO_INICIALES = [
    {
        "nombre": "LICENCIA_OPERADOR",
        "descripcion": "Documento de licencia vigente del operador",
        "aplica_a": "OPERADOR",
        "requiere_vigencia": True,
    },
    {
        "nombre": "TARJETA_CIRCULACION_TRAILER",
        "descripcion": "Tarjeta de circulacion vigente del trailer",
        "aplica_a": "TRAILER",
        "requiere_vigencia": True,
    },
    {
        "nombre": "TARJETA_CIRCULACION_CAJA",
        "descripcion": "Tarjeta de circulacion vigente de la caja",
        "aplica_a": "CAJA",
        "requiere_vigencia": True,
    },
    {
        "nombre": "DOCUMENTO_OPERATIVO_VIAJE",
        "descripcion": "Documento operativo general asociado al viaje",
        "aplica_a": "VIAJE",
        "requiere_vigencia": False,
    },
]


def seed_tipos_documento(db: Session) -> None:
    existentes = {
        row.nombre: row
        for row in db.query(TipoDocumento).all()
    }

    for item in TIPOS_DOCUMENTO_INICIALES:
        if item["nombre"] not in existentes:
            db.add(TipoDocumento(**item))

    db.commit()


def run_seed_documentos(db: Session) -> None:
    seed_tipos_documento(db)
