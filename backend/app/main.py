from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.routes_health import router as health_router
from app.api.routes_roles import router as roles_router
from app.api.routes_usuarios import router as usuarios_router
from app.api.routes_operadores import router as operadores_router
from app.api.routes_clientes import router as clientes_router
from app.api.routes_trailers import router as trailers_router
from app.api.routes_cajas import router as cajas_router
from app.api.routes_auth import router as auth_router
from app.api.routes_evidencias import router as evidencias_router
from app.api.routes_documentos import router as documentos_router
from app.api.routes_alertas import router as alertas_router
from app.api.routes_kpis import router as kpis_router
from app.api.routes_mantenimientos import router as mantenimientos_router
from app.api.routes_telegram import router as telegram_router
from app.api.routes_viajes import router as viajes_router
from app.db.base import Base
from app.db.database import SessionLocal, engine
from app.seeds.seed_documentos import run_seed_documentos
from app.seeds.seed_evidencias import run_seed_evidencias
from app.seeds.seed_roles import run_seed_roles
from app.seeds.seed_viajes import run_seed_viajes
import app.models  # noqa: F401


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS eventos_operativos_viaje ALTER COLUMN kilometraje DROP NOT NULL"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS eventos_operativos_viaje ALTER COLUMN nivel_diesel DROP NOT NULL"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS operadores ADD COLUMN IF NOT EXISTS rfc VARCHAR(20)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS operadores ADD COLUMN IF NOT EXISTS curp VARCHAR(30)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS operadores ADD COLUMN IF NOT EXISTS numero_expediente_medico VARCHAR(100)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS trailers ADD COLUMN IF NOT EXISTS permiso_circulacion VARCHAR(100)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS trailers ADD COLUMN IF NOT EXISTS numero_serie VARCHAR(150)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS cajas ADD COLUMN IF NOT EXISTS numero_serie VARCHAR(150)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS folio_viaje_cliente VARCHAR(150)"
        )
        connection.exec_driver_sql(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'viajes'
                      AND indexdef ILIKE 'CREATE UNIQUE INDEX%% (folio)%%'
                ) THEN
                    CREATE UNIQUE INDEX ux_viajes_folio ON viajes (folio);
                END IF;
            END
            $$;
            """
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS hora_cita_descarga TIME"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS fecha_carga DATE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS hora_carga TIME"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS fecha_descarga DATE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS hora_descarga TIME"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS lugar_inicio_latitud NUMERIC(10,7)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS lugar_inicio_longitud NUMERIC(10,7)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS lugar_destino_latitud NUMERIC(10,7)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS viajes ADD COLUMN IF NOT EXISTS lugar_destino_longitud NUMERIC(10,7)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS evidencias ADD COLUMN IF NOT EXISTS id_evento_operativo INTEGER"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS documentos ADD COLUMN IF NOT EXISTS comentario TEXT"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS documentos ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS documentos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"
        )
        connection.exec_driver_sql(
            "UPDATE documentos SET activo = TRUE WHERE activo IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE documentos SET updated_at = created_at WHERE updated_at IS NULL"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_archivos ADD COLUMN IF NOT EXISTS comentario TEXT"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_archivos ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_archivos ADD COLUMN IF NOT EXISTS created_by INTEGER"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_archivos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimientos ADD COLUMN IF NOT EXISTS fecha_mantenimiento DATE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimientos ADD COLUMN IF NOT EXISTS fecha_proximo_mantenimiento DATE"
        )
        connection.exec_driver_sql(
            "UPDATE mantenimientos SET fecha_mantenimiento = DATE(fecha_inicio) WHERE fecha_mantenimiento IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE viajes SET fecha_carga = DATE(fecha_programada_salida) WHERE fecha_carga IS NULL AND fecha_programada_salida IS NOT NULL"
        )
        connection.exec_driver_sql(
            "UPDATE viajes SET hora_carga = CAST(fecha_programada_salida AS TIME) WHERE hora_carga IS NULL AND fecha_programada_salida IS NOT NULL"
        )
        connection.exec_driver_sql(
            "UPDATE viajes SET fecha_descarga = fecha_entrega WHERE fecha_descarga IS NULL AND fecha_entrega IS NOT NULL"
        )
        connection.exec_driver_sql(
            "UPDATE viajes SET hora_descarga = COALESCE(hora_cita_descarga, hora_entrega) WHERE hora_descarga IS NULL AND (hora_cita_descarga IS NOT NULL OR hora_entrega IS NOT NULL)"
        )
        connection.exec_driver_sql(
            "UPDATE mantenimiento_archivos SET activo = TRUE WHERE activo IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE mantenimiento_archivos SET updated_at = created_at WHERE updated_at IS NULL"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_checklist_evidencias ADD COLUMN IF NOT EXISTS comentario TEXT"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_checklist_evidencias ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_checklist_evidencias ADD COLUMN IF NOT EXISTS created_by INTEGER"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS mantenimiento_checklist_evidencias ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"
        )
        connection.exec_driver_sql(
            "UPDATE mantenimiento_checklist_evidencias SET activo = TRUE WHERE activo IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE mantenimiento_checklist_evidencias SET updated_at = created_at WHERE updated_at IS NULL"
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS alertas (
                id_alerta SERIAL PRIMARY KEY,
                tipo_alerta VARCHAR(100) NOT NULL,
                entidad_tipo VARCHAR(50) NOT NULL,
                entidad_id INTEGER NOT NULL,
                mensaje TEXT NOT NULL,
                nivel VARCHAR(20) NOT NULL,
                leida BOOLEAN NOT NULL DEFAULT FALSE,
                requiere_notificacion BOOLEAN NOT NULL DEFAULT FALSE,
                notificada BOOLEAN NOT NULL DEFAULT FALSE,
                canal_notificacion VARCHAR(50),
                fecha_notificacion TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS alertas ADD COLUMN IF NOT EXISTS requiere_notificacion BOOLEAN DEFAULT FALSE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS alertas ADD COLUMN IF NOT EXISTS notificada BOOLEAN DEFAULT FALSE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS alertas ADD COLUMN IF NOT EXISTS canal_notificacion VARCHAR(50)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS alertas ADD COLUMN IF NOT EXISTS fecha_notificacion TIMESTAMP"
        )
        connection.exec_driver_sql(
            "UPDATE alertas SET requiere_notificacion = FALSE WHERE requiere_notificacion IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE alertas SET notificada = FALSE WHERE notificada IS NULL"
        )

    db: Session = SessionLocal()
    try:
        run_seed_roles(db)
        run_seed_viajes(db)
        run_seed_evidencias(db)
        run_seed_documentos(db)
    finally:
        db.close()


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(evidencias_router)
app.include_router(documentos_router)
app.include_router(alertas_router)
app.include_router(kpis_router)
app.include_router(mantenimientos_router)
app.include_router(telegram_router)
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
