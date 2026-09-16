from app.db.base import Base
from app.db.database import engine
import app.models  # noqa: F401
from sqlalchemy import text


_BITACORA_FUNCTION_BODY = """BEGIN
    RAISE EXCEPTION USING
        ERRCODE = '55000',
        MESSAGE = 'La bitácora de auditoría es inmutable';
END;"""
_BITACORA_FUNCTION_SQL = f"""
CREATE FUNCTION public.prevent_bitacora_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog
AS $bitacora$
{_BITACORA_FUNCTION_BODY}
$bitacora$
"""
_BITACORA_TRIGGER_SQL = """
CREATE TRIGGER trg_bitacora_eventos_immutable
BEFORE UPDATE OR DELETE ON public.bitacora_eventos
FOR EACH STATEMENT
EXECUTE FUNCTION public.prevent_bitacora_mutation()
"""


def _install_bitacora_immutability(connection) -> None:
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
        {"lock_name": "dafreq:bootstrap:bitacora_immutability"},
    )
    function_row = connection.execute(
        text(
            "SELECT p.oid, l.lanname, p.prosecdef, p.proconfig, p.prosrc, "
            "pg_catalog.pg_get_function_result(p.oid) AS result_type, "
            "pg_catalog.pg_get_function_identity_arguments(p.oid) AS arguments "
            "FROM pg_catalog.pg_proc p "
            "JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace "
            "JOIN pg_catalog.pg_language l ON l.oid = p.prolang "
            "WHERE n.nspname = 'public' "
            "AND p.proname = 'prevent_bitacora_mutation' "
            "AND pg_catalog.pg_get_function_identity_arguments(p.oid) = ''"
        )
    ).mappings().one_or_none()

    if function_row is None:
        connection.exec_driver_sql(_BITACORA_FUNCTION_SQL)
        function_oid = connection.execute(
            text("SELECT 'public.prevent_bitacora_mutation()'::regprocedure::oid")
        ).scalar_one()
    else:
        expected_config = ["search_path=pg_catalog"]
        function_is_compatible = (
            function_row["lanname"] == "plpgsql"
            and function_row["prosecdef"] is False
            and function_row["proconfig"] == expected_config
            and function_row["result_type"] == "trigger"
            and function_row["arguments"] == ""
            and function_row["prosrc"].strip(" \t\r\n") == _BITACORA_FUNCTION_BODY
        )
        if not function_is_compatible:
            raise RuntimeError(
                "La función public.prevent_bitacora_mutation() tiene una definición incompatible"
            )
        function_oid = function_row["oid"]

    trigger_rows = connection.execute(
        text(
            "SELECT t.oid, t.tgrelid, t.tgfoid, t.tgtype, t.tgenabled, t.tgqual, "
            "n.nspname AS table_schema, c.relname AS table_name "
            "FROM pg_catalog.pg_trigger t "
            "JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
            "WHERE t.tgname = 'trg_bitacora_eventos_immutable' "
            "AND NOT t.tgisinternal"
        )
    ).mappings().all()
    if not trigger_rows:
        connection.exec_driver_sql(_BITACORA_TRIGGER_SQL)
        return
    if len(trigger_rows) != 1:
        raise RuntimeError(
            "El trigger trg_bitacora_eventos_immutable tiene asociaciones incompatibles"
        )
    trigger = trigger_rows[0]
    trigger_is_compatible = (
        trigger["table_schema"] == "public"
        and trigger["table_name"] == "bitacora_eventos"
        and trigger["tgfoid"] == function_oid
        and trigger["tgtype"] == 26
        and trigger["tgenabled"] == "O"
        and trigger["tgqual"] is None
    )
    if not trigger_is_compatible:
        raise RuntimeError(
            "El trigger trg_bitacora_eventos_immutable tiene una definición incompatible"
        )


def run_schema_bootstrap() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS control_respaldo")

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        _install_bitacora_immutability(connection)
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
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id_subscription SERIAL PRIMARY KEY,
                id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
                endpoint VARCHAR(1000) NOT NULL UNIQUE,
                p256dh VARCHAR(255) NOT NULL,
                auth VARCHAR(255) NOT NULL,
                user_agent VARCHAR(500),
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                last_success_at TIMESTAMP,
                last_failure_at TIMESTAMP,
                failure_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS push_subscriptions ADD COLUMN IF NOT EXISTS user_agent VARCHAR(500)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS push_subscriptions ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS push_subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS push_subscriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS push_subscriptions ADD COLUMN IF NOT EXISTS last_success_at TIMESTAMP"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS push_subscriptions ADD COLUMN IF NOT EXISTS last_failure_at TIMESTAMP"
        )
        connection.exec_driver_sql(
            "ALTER TABLE IF EXISTS push_subscriptions ADD COLUMN IF NOT EXISTS failure_count INTEGER DEFAULT 0"
        )
        connection.exec_driver_sql(
            "UPDATE push_subscriptions SET activo = TRUE WHERE activo IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE push_subscriptions SET failure_count = 0 WHERE failure_count IS NULL"
        )

