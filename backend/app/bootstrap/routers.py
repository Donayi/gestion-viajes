from fastapi import FastAPI

from app.api.routes_alertas import router as alertas_router
from app.api.routes_auth import router as auth_router
from app.api.routes_cajas import router as cajas_router
from app.api.routes_clientes import router as clientes_router
from app.api.routes_documentos import router as documentos_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_evidencias import router as evidencias_router
from app.api.routes_health import router as health_router
from app.api.routes_kpis import router as kpis_router
from app.api.routes_mantenimientos import router as mantenimientos_router
from app.api.routes_operadores import router as operadores_router
from app.api.routes_push import router as push_router
from app.api.routes_respaldos import router as respaldos_router
from app.api.routes_roles import router as roles_router
from app.api.routes_telegram import router as telegram_router
from app.api.routes_trailers import router as trailers_router
from app.api.routes_usuarios import router as usuarios_router
from app.api.routes_viajes import router as viajes_router


def register_routers(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(evidencias_router)
    app.include_router(documentos_router)
    app.include_router(dashboard_router)
    app.include_router(alertas_router)
    app.include_router(kpis_router)
    app.include_router(mantenimientos_router)
    app.include_router(push_router)
    app.include_router(respaldos_router)
    app.include_router(telegram_router)
    app.include_router(roles_router)
    app.include_router(usuarios_router)
    app.include_router(operadores_router)
    app.include_router(clientes_router)
    app.include_router(trailers_router)
    app.include_router(cajas_router)
    app.include_router(viajes_router)
