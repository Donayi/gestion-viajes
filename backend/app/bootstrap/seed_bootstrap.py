from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.seeds.seed_documentos import run_seed_documentos
from app.seeds.seed_evidencias import run_seed_evidencias
from app.seeds.seed_roles import run_seed_roles
from app.seeds.seed_viajes import run_seed_viajes


def run_seed_bootstrap() -> None:
    db: Session = SessionLocal()
    try:
        run_seed_roles(db)
        run_seed_viajes(db)
        run_seed_evidencias(db)
        run_seed_documentos(db)
    finally:
        db.close()

