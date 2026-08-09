from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr


class RespaldoContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OrigenRespaldo(StrEnum):
    MANUAL = "MANUAL"
    AUTOMATICO = "AUTOMATICO"
    PRE_RESTAURACION = "PRE_RESTAURACION"
    IMPORTADO = "IMPORTADO"


class EstadoRespaldo(StrEnum):
    PENDIENTE = "PENDIENTE"
    GENERANDO = "GENERANDO"
    VALIDANDO = "VALIDANDO"
    DISPONIBLE = "DISPONIBLE"
    FALLIDO = "FALLIDO"
    CORRUPTO = "CORRUPTO"
    ELIMINADO = "ELIMINADO"


class TipoOperacionRespaldo(StrEnum):
    GENERACION = "GENERACION"
    CARGA = "CARGA"
    VALIDACION = "VALIDACION"
    DESCARGA = "DESCARGA"
    RESTAURACION = "RESTAURACION"
    RECUPERACION = "RECUPERACION"
    LIMPIEZA = "LIMPIEZA"


class EstadoOperacionRespaldo(StrEnum):
    PENDIENTE = "PENDIENTE"
    GENERANDO = "GENERANDO"
    VALIDANDO = "VALIDANDO"
    RESPALDO_PREVIO = "RESPALDO_PREVIO"
    BLOQUEANDO = "BLOQUEANDO"
    RESTAURANDO = "RESTAURANDO"
    VERIFICANDO = "VERIFICANDO"
    RECUPERANDO = "RECUPERANDO"
    DESCARGANDO = "DESCARGANDO"
    LIMPIANDO = "LIMPIANDO"
    EXITOSA = "EXITOSA"
    FALLIDA = "FALLIDA"
    FALLIDA_SIN_CAMBIOS = "FALLIDA_SIN_CAMBIOS"
    FALLIDA_RECUPERADA = "FALLIDA_RECUPERADA"
    FALLIDA_CRITICA = "FALLIDA_CRITICA"
    CANCELADA = "CANCELADA"
    INTERRUMPIDA = "INTERRUMPIDA"


class EstadoValidacionRespaldo(StrEnum):
    PENDIENTE = "PENDIENTE"
    VALIDO = "VALIDO"
    INVALIDO = "INVALIDO"
    EXPIRADO = "EXPIRADO"


class ResultadoFinalRestauracion(StrEnum):
    EXITOSA = "EXITOSA"
    FALLIDA_SIN_CAMBIOS = "FALLIDA_SIN_CAMBIOS"
    FALLIDA_RECUPERADA = "FALLIDA_RECUPERADA"
    FALLIDA_CRITICA = "FALLIDA_CRITICA"


class ErrorSanitizadoRespaldo(RespaldoContract):
    codigo: str = Field(min_length=1, max_length=100)
    mensaje: str = Field(min_length=1, max_length=500)
    recuperable: bool = False


class ConteoTablaRespaldo(RespaldoContract):
    schema_name: str = Field(min_length=1, max_length=63)
    table_name: str = Field(min_length=1, max_length=63)
    row_count: int = Field(ge=0)


class ResumenManifiestoRespaldo(RespaldoContract):
    format: str = Field(default="dafreq-backup", min_length=1, max_length=50)
    format_version: int = Field(ge=1)
    created_at: AwareDatetime
    application_version: str = Field(min_length=1, max_length=100)
    postgres_server_major: int = Field(default=16, ge=1)
    postgres_dump_format: str = Field(default="custom", min_length=1, max_length=30)
    included_schemas: list[str] = Field(default_factory=lambda: ["public"], max_length=10)
    excluded_schemas: list[str] = Field(
        default_factory=lambda: ["control_respaldo"],
        max_length=10,
    )
    includes_r2_objects: bool = False
    includes_r2_metadata: bool = True
    table_count: int = Field(ge=0)
    row_count: int = Field(ge=0)
    tables: list[ConteoTablaRespaldo] = Field(default_factory=list)


class SolicitudRespaldoManual(RespaldoContract):
    motivo: str | None = Field(default=None, max_length=500)


class RespuestaRespaldo(RespaldoContract):
    id_respaldo: UUID
    nombre_archivo: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^.+\.dafreq-backup$",
    )
    origen: OrigenRespaldo
    estado: EstadoRespaldo
    size_bytes: int | None = Field(default=None, ge=0)
    created_at: AwareDatetime
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    validated_at: AwareDatetime | None = None
    creado_por_id_original: int | None = Field(default=None, ge=1)
    creado_por_username: str | None = Field(default=None, max_length=150)
    creado_por_rol: str | None = Field(default=None, max_length=100)
    manifiesto: ResumenManifiestoRespaldo | None = None
    error: ErrorSanitizadoRespaldo | None = None


class ListaPaginadaRespaldos(RespaldoContract):
    items: list[RespuestaRespaldo]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class RespaldoAdministrativo(RespaldoContract):
    id_respaldo: UUID
    nombre_archivo: str = Field(min_length=1, max_length=255)
    origen: OrigenRespaldo
    estado: EstadoRespaldo
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    table_count: int | None = Field(default=None, ge=0)
    row_count: int | None = Field(default=None, ge=0)
    created_at: AwareDatetime
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    error_mensaje: str | None = Field(default=None, max_length=500)


class ListaRespaldosAdministrativos(RespaldoContract):
    items: list[RespaldoAdministrativo]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class RespuestaOperacionRespaldo(RespaldoContract):
    id_operacion: UUID
    tipo: TipoOperacionRespaldo
    estado: EstadoOperacionRespaldo
    id_respaldo: UUID | None = None
    id_respaldo_seguridad: UUID | None = None
    created_at: AwareDatetime
    started_at: AwareDatetime | None = None
    heartbeat_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    resultado_restauracion: ResultadoFinalRestauracion | None = None
    progreso_porcentaje: int | None = Field(default=None, ge=0, le=100)
    mensaje: str | None = Field(default=None, max_length=500)
    error: ErrorSanitizadoRespaldo | None = None


class RespuestaValidacionRespaldo(RespaldoContract):
    id_validacion: UUID
    id_respaldo: UUID
    estado: EstadoValidacionRespaldo
    format_version: int = Field(ge=1)
    created_at: AwareDatetime
    expires_at: AwareDatetime
    manifiesto: ResumenManifiestoRespaldo | None = None
    advertencias: list[str] = Field(default_factory=list, max_length=100)
    error: ErrorSanitizadoRespaldo | None = None


class SolicitudDesafioRestauracion(RespaldoContract):
    password: SecretStr = Field(min_length=1, max_length=72)


class RespuestaDesafioRestauracion(RespaldoContract):
    id_confirmacion: UUID
    challenge_token: str = Field(min_length=32, max_length=512)
    confirmation_phrase: str = Field(min_length=1, max_length=100)
    expires_at: AwareDatetime


class SolicitudRestauracion(RespaldoContract):
    challenge_token: SecretStr = Field(min_length=32, max_length=512)
    confirmation_phrase: str = Field(min_length=1, max_length=100)


class RespuestaTicketDescarga(RespaldoContract):
    id_ticket: UUID
    ticket_token: str = Field(min_length=32, max_length=512)
    expires_at: AwareDatetime
    one_time_use: bool = True


class EstadoMantenimientoRespaldo(RespaldoContract):
    activo: bool
    mensaje: str = Field(min_length=1, max_length=255)
    id_operacion: UUID | None = None
    resultado_restauracion: ResultadoFinalRestauracion | None = None
    updated_at: AwareDatetime


__all__ = [
    "ConteoTablaRespaldo",
    "ErrorSanitizadoRespaldo",
    "EstadoMantenimientoRespaldo",
    "EstadoOperacionRespaldo",
    "EstadoRespaldo",
    "EstadoValidacionRespaldo",
    "ListaPaginadaRespaldos",
    "OrigenRespaldo",
    "RespuestaDesafioRestauracion",
    "RespuestaOperacionRespaldo",
    "RespuestaRespaldo",
    "RespuestaTicketDescarga",
    "RespuestaValidacionRespaldo",
    "ResultadoFinalRestauracion",
    "ResumenManifiestoRespaldo",
    "SolicitudDesafioRestauracion",
    "SolicitudRespaldoManual",
    "SolicitudRestauracion",
    "TipoOperacionRespaldo",
]
