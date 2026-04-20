from sqlalchemy.orm import Session

from app.models.models import CatalogoEstatusViaje, TransicionEstatusViaje


ESTATUS_INICIALES = [
    {
        "clave": "CREADO",
        "nombre": "Creado",
        "descripcion": "Viaje creado por administración",
        "orden_flujo": 1,
        "es_terminal": False,
        "requiere_evidencia": False,
        "activo": True,
    },
    {
        "clave": "ASIGNADO",
        "nombre": "Asignado",
        "descripcion": "Viaje asignado a operador y/o tráiler",
        "orden_flujo": 2,
        "es_terminal": False,
        "requiere_evidencia": False,
        "activo": True,
    },
    {
        "clave": "CARGANDO",
        "nombre": "Cargando",
        "descripcion": "Operador en proceso de carga previo al recorrido",
        "orden_flujo": 3,
        "es_terminal": False,
        "requiere_evidencia": False,
        "activo": True,
    },
    {
        "clave": "INICIADO",
        "nombre": "Iniciado",
        "descripcion": "Viaje iniciado formalmente con evidencia y documentos",
        "orden_flujo": 4,
        "es_terminal": False,
        "requiere_evidencia": True,
        "activo": True,
    },
    {
        "clave": "RETRASADO",
        "nombre": "Retrasado",
        "descripcion": "Viaje activo con retraso o percance",
        "orden_flujo": 5,
        "es_terminal": False,
        "requiere_evidencia": False,
        "activo": True,
    },
    {
        "clave": "STANDBY",
        "nombre": "Standby",
        "descripcion": "Viaje en resguardo o pausa operativa sin cierre",
        "orden_flujo": 6,
        "es_terminal": False,
        "requiere_evidencia": False,
        "activo": True,
    },
    {
        "clave": "FINALIZADO",
        "nombre": "Finalizado",
        "descripcion": "Viaje terminado con evidencias de cierre",
        "orden_flujo": 7,
        "es_terminal": True,
        "requiere_evidencia": True,
        "activo": True,
    },
    {
        "clave": "CANCELADO",
        "nombre": "Cancelado",
        "descripcion": "Viaje cancelado sin concluir operación",
        "orden_flujo": 8,
        "es_terminal": True,
        "requiere_evidencia": False,
        "activo": True,
    },
]


TRANSICIONES_INICIALES = [
    ("CREADO", "ASIGNADO", False, False),
    ("ASIGNADO", "CARGANDO", False, False),
    ("CARGANDO", "INICIADO", False, True),
    ("INICIADO", "RETRASADO", True, False),
    ("RETRASADO", "INICIADO", True, False),
    ("INICIADO", "STANDBY", True, False),
    ("STANDBY", "ASIGNADO", True, False),
    ("STANDBY", "CARGANDO", True, False),
    ("INICIADO", "FINALIZADO", False, True),
    ("RETRASADO", "FINALIZADO", True, True),
    ("CREADO", "CANCELADO", True, False),
    ("ASIGNADO", "CANCELADO", True, False),
    ("CARGANDO", "CANCELADO", True, False),
    ("STANDBY", "CANCELADO", True, False),
]


def seed_catalogo_estatus_viaje(db: Session) -> None:
    existentes = {
        row.clave: row
        for row in db.query(CatalogoEstatusViaje).all()
    }

    for item in ESTATUS_INICIALES:
        if item["clave"] not in existentes:
            db.add(CatalogoEstatusViaje(**item))

    db.commit()


def seed_transiciones_estatus_viaje(db: Session) -> None:
    estatus = {
        row.clave: row
        for row in db.query(CatalogoEstatusViaje).all()
    }

    existentes = {
        (row.id_estatus_origen, row.id_estatus_destino)
        for row in db.query(TransicionEstatusViaje).all()
    }

    for clave_origen, clave_destino, requiere_comentario, requiere_evidencia in TRANSICIONES_INICIALES:
        origen = estatus.get(clave_origen)
        destino = estatus.get(clave_destino)

        if not origen or not destino:
            continue

        llave = (origen.id_estatus, destino.id_estatus)
        if llave in existentes:
            continue

        db.add(
            TransicionEstatusViaje(
                id_estatus_origen=origen.id_estatus,
                id_estatus_destino=destino.id_estatus,
                requiere_comentario=requiere_comentario,
                requiere_evidencia=requiere_evidencia,
                activo=True,
            )
        )

    db.commit()


def run_seed_viajes(db: Session) -> None:
    seed_catalogo_estatus_viaje(db)
    seed_transiciones_estatus_viaje(db)