from sqlalchemy.orm import Session

from app.models.models import ArchivoStorage, TipoEvidencia


TIPOS_EVIDENCIA_INICIALES = [
    {
        "nombre": "EVIDENCIA_INICIO",
        "descripcion": "Evidencia general para habilitar el inicio del viaje",
    },
    {
        "nombre": "EVIDENCIA_CIERRE",
        "descripcion": "Evidencia general para habilitar el cierre del viaje",
    },
    {
        "nombre": "EVIDENCIA_GENERAL",
        "descripcion": "Evidencia operativa reutilizable durante el viaje",
    },
]


ARCHIVOS_STORAGE_PRUEBA = [
    {
        "proveedor": "LOCAL_MOCK",
        "bucket": "mock-viajes",
        "file_key": "seed/evidencias/inicio-001.jpg",
        "nombre_original": "inicio-001.jpg",
        "nombre_guardado": "inicio-001.jpg",
        "extension": ".jpg",
        "content_type": "image/jpeg",
        "size_bytes": 1024,
        "etag": "seed-inicio-001",
        "hash_sha256": "seedhash-inicio-001",
        "url_publica": "https://mock.local/evidencias/inicio-001.jpg",
        "subido_por": None,
    },
    {
        "proveedor": "LOCAL_MOCK",
        "bucket": "mock-viajes",
        "file_key": "seed/evidencias/cierre-001.jpg",
        "nombre_original": "cierre-001.jpg",
        "nombre_guardado": "cierre-001.jpg",
        "extension": ".jpg",
        "content_type": "image/jpeg",
        "size_bytes": 2048,
        "etag": "seed-cierre-001",
        "hash_sha256": "seedhash-cierre-001",
        "url_publica": "https://mock.local/evidencias/cierre-001.jpg",
        "subido_por": None,
    },
    {
        "proveedor": "LOCAL_MOCK",
        "bucket": "mock-viajes",
        "file_key": "seed/evidencias/general-001.pdf",
        "nombre_original": "general-001.pdf",
        "nombre_guardado": "general-001.pdf",
        "extension": ".pdf",
        "content_type": "application/pdf",
        "size_bytes": 4096,
        "etag": "seed-general-001",
        "hash_sha256": "seedhash-general-001",
        "url_publica": "https://mock.local/evidencias/general-001.pdf",
        "subido_por": None,
    },
]


def seed_tipos_evidencia(db: Session) -> None:
    existentes = {
        row.nombre: row
        for row in db.query(TipoEvidencia).all()
    }

    for item in TIPOS_EVIDENCIA_INICIALES:
        if item["nombre"] not in existentes:
            db.add(TipoEvidencia(**item))

    db.commit()


def seed_archivos_storage_prueba(db: Session) -> None:
    existentes = {
        row.file_key: row
        for row in db.query(ArchivoStorage).all()
    }

    for item in ARCHIVOS_STORAGE_PRUEBA:
        if item["file_key"] not in existentes:
            db.add(ArchivoStorage(**item))

    db.commit()


def run_seed_evidencias(db: Session) -> None:
    seed_tipos_evidencia(db)
    seed_archivos_storage_prueba(db)
