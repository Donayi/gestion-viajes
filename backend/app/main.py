from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.routes_health import router as health_router
from app.api.routes_roles import router as roles_router
from app.api.routes_usuarios import router as usuarios_router
from app.api.routes_operadores import router as operadores_router
from app.api.routes_clientes import router as clientes_router
from app.api.routes_trailers import router as trailers_router
from app.api.routes_cajas import router as cajas_router
from app.api.routes_viajes import router as viajes_router
from app.db.base import Base
from app.db.database import SessionLocal, engine
from app.seeds.seed_evidencias import run_seed_evidencias
from app.seeds.seed_viajes import run_seed_viajes
import app.models  # noqa: F401


app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        run_seed_viajes(db)
        run_seed_evidencias(db)
    finally:
        db.close()


app.include_router(health_router)
app.include_router(roles_router)
app.include_router(usuarios_router)
app.include_router(operadores_router)
app.include_router(clientes_router)
app.include_router(trailers_router)
app.include_router(cajas_router)
app.include_router(viajes_router)


@app.get("/")
def root():
    return {"message": f"{settings.app_name} funcionando"}
