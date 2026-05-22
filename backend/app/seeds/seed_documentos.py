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
        "nombre": "ESTUDIO_MEDICO_OPERADOR",
        "descripcion": "Estudio medico del operador",
        "aplica_a": "OPERADOR",
        "requiere_vigencia": True,
    },
    {
        "nombre": "SUA_OPERADOR",
        "descripcion": "Documento SUA del operador",
        "aplica_a": "OPERADOR",
        "requiere_vigencia": True,
    },
    {
        "nombre": "IDENTIFICACION_OPERADOR",
        "descripcion": "Identificacion oficial del operador",
        "aplica_a": "OPERADOR",
        "requiere_vigencia": False,
    },
    {
        "nombre": "RFC_OPERADOR",
        "descripcion": "Constancia RFC del operador",
        "aplica_a": "OPERADOR",
        "requiere_vigencia": False,
    },
    {
        "nombre": "CURP_OPERADOR",
        "descripcion": "Documento CURP del operador",
        "aplica_a": "OPERADOR",
        "requiere_vigencia": False,
    },
    {
        "nombre": "TARJETA_CIRCULACION_TRAILER",
        "descripcion": "Tarjeta de circulacion vigente del trailer",
        "aplica_a": "TRAILER",
        "requiere_vigencia": True,
    },
    {
        "nombre": "POLIZA_SEGURO_TRAILER",
        "descripcion": "Poliza de seguro del trailer",
        "aplica_a": "TRAILER",
        "requiere_vigencia": True,
    },
    {
        "nombre": "VERIFICACION_TRAILER",
        "descripcion": "Documento de verificacion del trailer",
        "aplica_a": "TRAILER",
        "requiere_vigencia": True,
    },
    {
        "nombre": "PERMISO_CIRCULACION_TRAILER",
        "descripcion": "Permiso de circulacion del trailer",
        "aplica_a": "TRAILER",
        "requiere_vigencia": True,
    },
    {
        "nombre": "FACTURA_TRAILER",
        "descripcion": "Documento de propiedad o factura del trailer",
        "aplica_a": "TRAILER",
        "requiere_vigencia": False,
    },
    {
        "nombre": "TARJETA_CIRCULACION_CAJA",
        "descripcion": "Tarjeta de circulacion vigente de la caja",
        "aplica_a": "CAJA",
        "requiere_vigencia": True,
    },
    {
        "nombre": "VERIFICACION_CAJA",
        "descripcion": "Documento de verificacion de la caja",
        "aplica_a": "CAJA",
        "requiere_vigencia": True,
    },
    {
        "nombre": "FACTURA_CAJA",
        "descripcion": "Documento de propiedad o factura de la caja",
        "aplica_a": "CAJA",
        "requiere_vigencia": False,
    },
    {
        "nombre": "NUMERO_SERIE_CAJA",
        "descripcion": "Documento relacionado con el numero de serie de la caja",
        "aplica_a": "CAJA",
        "requiere_vigencia": False,
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
