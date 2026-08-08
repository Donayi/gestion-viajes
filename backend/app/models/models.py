from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


CONTROL_RESPALDO_SCHEMA = "control_respaldo"


class Rol(Base):
    __tablename__ = "roles"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    usuarios = relationship("Usuario", back_populates="rol")


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    apellido: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha_nacimiento: Mapped[Date | None] = mapped_column(Date, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    id_rol: Mapped[int] = mapped_column(ForeignKey("roles.id_rol"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    rol = relationship("Rol", back_populates="usuarios")
    operador = relationship("Operador", back_populates="usuario", uselist=False)

    viajes_creados = relationship(
        "Viaje",
        foreign_keys="Viaje.created_by",
        back_populates="usuario_creador",
    )
    viajes_actualizados = relationship(
        "Viaje",
        foreign_keys="Viaje.updated_by",
        back_populates="usuario_actualizador",
    )

    historial_cambios = relationship(
        "HistorialEstatusViaje",
        back_populates="usuario_cambio",
    )

    archivos_subidos = relationship("ArchivoStorage", back_populates="usuario_subio")
    documentos_subidos = relationship("Documento", back_populates="usuario_subio")
    eventos_operativos_creados = relationship(
        "EventoOperativoViaje",
        back_populates="usuario_creador",
    )

    asignaciones_creadas = relationship(
        "AsignacionViaje",
        back_populates="usuario_creador",
    )
    push_subscriptions = relationship("PushSubscription", back_populates="usuario")


class Operador(Base):
    __tablename__ = "operadores"

    id_operador: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=False, unique=True)
    alias: Mapped[str] = mapped_column(String(150), nullable=False)
    numero_licencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rfc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    curp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    numero_expediente_medico: Mapped[str | None] = mapped_column(String(100), nullable=True)
    licencia_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    sua: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sua_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    estudio_medico: Mapped[Date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    usuario = relationship("Usuario", back_populates="operador")

    viajes_actuales = relationship(
        "Viaje",
        foreign_keys="Viaje.id_operador_actual",
        back_populates="operador_actual",
    )
    asignaciones = relationship("AsignacionViaje", back_populates="operador")

    documentos = relationship("Documento", back_populates="operador")
    evidencias = relationship("Evidencia", back_populates="operador")
    eventos_operativos = relationship("EventoOperativoViaje", back_populates="operador")
    incidencias = relationship("Incidencia", back_populates="operador")


class Trailer(Base):
    __tablename__ = "trailers"

    id_trailer: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_economico: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    placas: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    marca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poliza_seguro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seguro_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    tarjeta_circulacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tarjeta_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    permiso_circulacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(150), nullable=True)
    verificacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verificacion_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    viajes_actuales = relationship(
        "Viaje",
        foreign_keys="Viaje.id_trailer_actual",
        back_populates="trailer_actual",
    )
    asignaciones = relationship("AsignacionViaje", back_populates="trailer")

    documentos = relationship("Documento", back_populates="trailer")
    eventos_operativos = relationship("EventoOperativoViaje", back_populates="trailer")
    mantenimientos = relationship("Mantenimiento", back_populates="trailer")


class Caja(Base):
    __tablename__ = "cajas"

    id_caja: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_economico: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    placas: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    tipo_caja: Mapped[str | None] = mapped_column(String(100), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poliza_seguro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seguro_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    tarjeta_circulacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tarjeta_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(150), nullable=True)
    verificacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verificacion_vigencia: Mapped[Date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    viajes_actuales = relationship(
        "Viaje",
        foreign_keys="Viaje.id_caja_actual",
        back_populates="caja_actual",
    )
    asignaciones = relationship("AsignacionViaje", back_populates="caja")

    documentos = relationship("Documento", back_populates="caja")
    eventos_operativos = relationship("EventoOperativoViaje", back_populates="caja")
    mantenimientos = relationship("Mantenimiento", back_populates="caja")


class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_razon_social: Mapped[str] = mapped_column(String(255), nullable=False)
    rfc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    regimen_fiscal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tiempo_credito: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contacto_nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contacto_telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contacto_email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    viajes = relationship("Viaje", back_populates="cliente")


class CatalogoEstatusViaje(Base):
    __tablename__ = "catalogo_estatus_viaje"

    id_estatus: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    orden_flujo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    es_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    requiere_evidencia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    viajes_actuales = relationship("Viaje", back_populates="estatus_actual")

    historial = relationship("HistorialEstatusViaje", back_populates="estatus")

    transiciones_origen = relationship(
        "TransicionEstatusViaje",
        foreign_keys="TransicionEstatusViaje.id_estatus_origen",
        back_populates="estatus_origen",
    )
    transiciones_destino = relationship(
        "TransicionEstatusViaje",
        foreign_keys="TransicionEstatusViaje.id_estatus_destino",
        back_populates="estatus_destino",
    )


class Viaje(Base):
    __tablename__ = "viajes"

    id_viaje: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    folio: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    folio_viaje_cliente: Mapped[str | None] = mapped_column(String(150), nullable=True)
    id_cliente: Mapped[int] = mapped_column(ForeignKey("clientes.id_cliente"), nullable=False)

    lugar_inicio: Mapped[str] = mapped_column(String(255), nullable=False)
    lugar_destino: Mapped[str] = mapped_column(String(255), nullable=False)
    lugar_inicio_latitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lugar_inicio_longitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lugar_destino_latitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lugar_destino_longitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    tipo_carga: Mapped[str | None] = mapped_column(String(150), nullable=True)
    descripcion_carga: Mapped[str | None] = mapped_column(Text, nullable=True)

    id_estatus_actual: Mapped[int] = mapped_column(
        ForeignKey("catalogo_estatus_viaje.id_estatus"),
        nullable=False,
    )

    id_operador_actual: Mapped[int | None] = mapped_column(
        ForeignKey("operadores.id_operador"),
        nullable=True,
    )
    id_trailer_actual: Mapped[int | None] = mapped_column(
        ForeignKey("trailers.id_trailer"),
        nullable=True,
    )
    id_caja_actual: Mapped[int | None] = mapped_column(
        ForeignKey("cajas.id_caja"),
        nullable=True,
    )

    fecha_programada_salida: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    fecha_carga: Mapped[Date | None] = mapped_column(Date, nullable=True)
    hora_carga: Mapped[Time | None] = mapped_column(Time, nullable=True)
    fecha_inicio: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    fecha_llegada: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    fecha_descarga: Mapped[Date | None] = mapped_column(Date, nullable=True)
    hora_descarga: Mapped[Time | None] = mapped_column(Time, nullable=True)
    fecha_entrega: Mapped[Date | None] = mapped_column(Date, nullable=True)
    hora_entrega: Mapped[Time | None] = mapped_column(Time, nullable=True)
    hora_cita_descarga: Mapped[Time | None] = mapped_column(Time, nullable=True)

    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id_usuario"),
        nullable=True,
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id_usuario"),
        nullable=True,
    )

    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    cliente = relationship("Cliente", back_populates="viajes")
    estatus_actual = relationship("CatalogoEstatusViaje", back_populates="viajes_actuales")

    operador_actual = relationship(
        "Operador",
        foreign_keys=[id_operador_actual],
        back_populates="viajes_actuales",
    )
    trailer_actual = relationship(
        "Trailer",
        foreign_keys=[id_trailer_actual],
        back_populates="viajes_actuales",
    )
    caja_actual = relationship(
        "Caja",
        foreign_keys=[id_caja_actual],
        back_populates="viajes_actuales",
    )

    usuario_creador = relationship(
        "Usuario",
        foreign_keys=[created_by],
        back_populates="viajes_creados",
    )
    usuario_actualizador = relationship(
        "Usuario",
        foreign_keys=[updated_by],
        back_populates="viajes_actualizados",
    )

    historial_estatus = relationship("HistorialEstatusViaje", back_populates="viaje")
    asignaciones = relationship("AsignacionViaje", back_populates="viaje")
    eventos_operativos = relationship(
        "EventoOperativoViaje",
        back_populates="viaje",
        order_by="desc(EventoOperativoViaje.created_at)",
    )

    documentos = relationship("Documento", back_populates="viaje")
    evidencias = relationship("Evidencia", back_populates="viaje")
    incidencias = relationship("Incidencia", back_populates="viaje")


class HistorialEstatusViaje(Base):
    __tablename__ = "historial_estatus_viaje"

    id_historial: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_viaje: Mapped[int] = mapped_column(ForeignKey("viajes.id_viaje"), nullable=False)
    id_estatus: Mapped[int] = mapped_column(
        ForeignKey("catalogo_estatus_viaje.id_estatus"),
        nullable=False,
    )
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    changed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    viaje = relationship("Viaje", back_populates="historial_estatus")
    estatus = relationship("CatalogoEstatusViaje", back_populates="historial")
    usuario_cambio = relationship("Usuario", back_populates="historial_cambios")


class AsignacionViaje(Base):
    __tablename__ = "asignaciones_viaje"

    id_asignacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_viaje: Mapped[int] = mapped_column(ForeignKey("viajes.id_viaje"), nullable=False)

    id_operador: Mapped[int | None] = mapped_column(ForeignKey("operadores.id_operador"), nullable=True)
    id_trailer: Mapped[int | None] = mapped_column(ForeignKey("trailers.id_trailer"), nullable=True)
    id_caja: Mapped[int | None] = mapped_column(ForeignKey("cajas.id_caja"), nullable=True)

    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    fecha_asignacion: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    fecha_inicio_operacion: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    fecha_fin_asignacion: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    motivo: Mapped[str | None] = mapped_column(String(150), nullable=True)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    viaje = relationship("Viaje", back_populates="asignaciones")
    operador = relationship("Operador", back_populates="asignaciones")
    trailer = relationship("Trailer", back_populates="asignaciones")
    caja = relationship("Caja", back_populates="asignaciones")
    usuario_creador = relationship("Usuario", back_populates="asignaciones_creadas")


class EventoOperativoViaje(Base):
    __tablename__ = "eventos_operativos_viaje"

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_viaje: Mapped[int] = mapped_column(ForeignKey("viajes.id_viaje"), nullable=False)
    id_operador: Mapped[int | None] = mapped_column(ForeignKey("operadores.id_operador"), nullable=True)
    id_trailer: Mapped[int | None] = mapped_column(ForeignKey("trailers.id_trailer"), nullable=True)
    id_caja: Mapped[int | None] = mapped_column(ForeignKey("cajas.id_caja"), nullable=True)
    tipo_evento: Mapped[str] = mapped_column(String(50), nullable=False)
    kilometraje: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    nivel_diesel: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    ubicacion: Mapped[str] = mapped_column(String(255), nullable=False)
    latitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    viaje = relationship("Viaje", back_populates="eventos_operativos")
    operador = relationship("Operador", back_populates="eventos_operativos")
    trailer = relationship("Trailer", back_populates="eventos_operativos")
    caja = relationship("Caja", back_populates="eventos_operativos")
    usuario_creador = relationship("Usuario", back_populates="eventos_operativos_creados")
    evidencias = relationship("Evidencia", back_populates="evento_operativo")


class TransicionEstatusViaje(Base):
    __tablename__ = "transiciones_estatus_viaje"
    __table_args__ = (
        UniqueConstraint(
            "id_estatus_origen",
            "id_estatus_destino",
            name="uq_transicion_estatus",
        ),
    )

    id_transicion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_estatus_origen: Mapped[int] = mapped_column(
        ForeignKey("catalogo_estatus_viaje.id_estatus"),
        nullable=False,
    )
    id_estatus_destino: Mapped[int] = mapped_column(
        ForeignKey("catalogo_estatus_viaje.id_estatus"),
        nullable=False,
    )
    requiere_comentario: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    requiere_evidencia: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    estatus_origen = relationship(
        "CatalogoEstatusViaje",
        foreign_keys=[id_estatus_origen],
        back_populates="transiciones_origen",
    )
    estatus_destino = relationship(
        "CatalogoEstatusViaje",
        foreign_keys=[id_estatus_destino],
        back_populates="transiciones_destino",
    )


class TipoDocumento(Base):
    __tablename__ = "tipos_documento"

    id_tipo_documento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aplica_a: Mapped[str] = mapped_column(String(50), nullable=False)
    requiere_vigencia: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    documentos = relationship("Documento", back_populates="tipo_documento")


class ArchivoStorage(Base):
    __tablename__ = "archivos_storage"

    id_archivo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proveedor: Mapped[str] = mapped_column(
        String(50), nullable=False, default="CLOUDFLARE_R2", server_default="CLOUDFLARE_R2"
    )
    bucket: Mapped[str] = mapped_column(String(150), nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    nombre_original: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nombre_guardado: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url_publica: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    usuario_subio = relationship("Usuario", back_populates="archivos_subidos")
    documentos = relationship("Documento", back_populates="archivo")
    evidencias = relationship("Evidencia", back_populates="archivo")
    mantenimientos_archivos = relationship("MantenimientoArchivo", back_populates="archivo")
    incidencias_archivos = relationship("IncidenciaArchivo", back_populates="archivo")


class Documento(Base):
    __tablename__ = "documentos"
    __table_args__ = (
        CheckConstraint(
            """
            (
                (CASE WHEN id_operador IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN id_trailer IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN id_caja IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN id_viaje IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1
            """,
            name="ck_documentos_una_sola_entidad",
        ),
    )

    id_documento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_tipo_documento: Mapped[int] = mapped_column(ForeignKey("tipos_documento.id_tipo_documento"), nullable=False)
    id_operador: Mapped[int | None] = mapped_column(ForeignKey("operadores.id_operador"), nullable=True)
    id_trailer: Mapped[int | None] = mapped_column(ForeignKey("trailers.id_trailer"), nullable=True)
    id_caja: Mapped[int | None] = mapped_column(ForeignKey("cajas.id_caja"), nullable=True)
    id_viaje: Mapped[int | None] = mapped_column(ForeignKey("viajes.id_viaje"), nullable=True)
    id_archivo: Mapped[int] = mapped_column(ForeignKey("archivos_storage.id_archivo"), nullable=False)
    fecha_emision: Mapped[Date | None] = mapped_column(Date, nullable=True)
    fecha_expiracion: Mapped[Date | None] = mapped_column(Date, nullable=True)
    estatus: Mapped[str] = mapped_column(
        String(50), nullable=False, default="VIGENTE", server_default="VIGENTE"
    )
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tipo_documento = relationship("TipoDocumento", back_populates="documentos")
    operador = relationship("Operador", back_populates="documentos")
    trailer = relationship("Trailer", back_populates="documentos")
    caja = relationship("Caja", back_populates="documentos")
    viaje = relationship("Viaje", back_populates="documentos")
    archivo = relationship("ArchivoStorage", back_populates="documentos")
    usuario_subio = relationship("Usuario", back_populates="documentos_subidos")

    @property
    def entidad_tipo(self) -> str | None:
        if self.id_operador is not None:
            return "OPERADOR"
        if self.id_trailer is not None:
            return "TRAILER"
        if self.id_caja is not None:
            return "CAJA"
        if self.id_viaje is not None:
            return "VIAJE"
        return None

    @property
    def entidad_id(self) -> int | None:
        if self.id_operador is not None:
            return self.id_operador
        if self.id_trailer is not None:
            return self.id_trailer
        if self.id_caja is not None:
            return self.id_caja
        if self.id_viaje is not None:
            return self.id_viaje
        return None

    @property
    def fecha_vencimiento(self) -> Date | None:
        return self.fecha_expiracion


class TipoEvidencia(Base):
    __tablename__ = "tipos_evidencia"

    id_tipo_evidencia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    evidencias = relationship("Evidencia", back_populates="tipo_evidencia")


class Evidencia(Base):
    __tablename__ = "evidencias"

    id_evidencia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_viaje: Mapped[int] = mapped_column(ForeignKey("viajes.id_viaje"), nullable=False)
    id_evento_operativo: Mapped[int | None] = mapped_column(
        ForeignKey("eventos_operativos_viaje.id_evento"),
        nullable=True,
    )
    id_tipo_evidencia: Mapped[int] = mapped_column(ForeignKey("tipos_evidencia.id_tipo_evidencia"), nullable=False)
    id_operador: Mapped[int | None] = mapped_column(ForeignKey("operadores.id_operador"), nullable=True)
    id_archivo: Mapped[int] = mapped_column(ForeignKey("archivos_storage.id_archivo"), nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_captura: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    latitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    viaje = relationship("Viaje", back_populates="evidencias")
    evento_operativo = relationship("EventoOperativoViaje", back_populates="evidencias")
    tipo_evidencia = relationship("TipoEvidencia", back_populates="evidencias")
    operador = relationship("Operador", back_populates="evidencias")
    archivo = relationship("ArchivoStorage", back_populates="evidencias")


class Mantenimiento(Base):
    __tablename__ = "mantenimientos"
    __table_args__ = (
        CheckConstraint(
            """
            (
                (CASE WHEN id_trailer IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN id_caja IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1
            """,
            name="ck_mantenimientos_una_sola_entidad",
        ),
    )

    id_mantenimiento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entidad_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    id_trailer: Mapped[int | None] = mapped_column(ForeignKey("trailers.id_trailer"), nullable=True)
    id_caja: Mapped[int | None] = mapped_column(ForeignKey("cajas.id_caja"), nullable=True)
    tipo_mantenimiento: Mapped[str] = mapped_column(String(30), nullable=False)
    estatus: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ABIERTO", server_default="ABIERTO"
    )
    fecha_inicio: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    fecha_mantenimiento: Mapped[Date | None] = mapped_column(Date, nullable=True)
    fecha_proximo_mantenimiento: Mapped[Date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    kilometraje: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    trailer = relationship("Trailer", back_populates="mantenimientos")
    caja = relationship("Caja", back_populates="mantenimientos")
    usuario_creador = relationship("Usuario", foreign_keys=[created_by])
    usuario_actualizador = relationship("Usuario", foreign_keys=[updated_by])
    checklist_items = relationship(
        "MantenimientoChecklistItem",
        back_populates="mantenimiento",
        cascade="all, delete-orphan",
        order_by="MantenimientoChecklistItem.id_item.asc()",
    )
    archivos = relationship(
        "MantenimientoArchivo",
        back_populates="mantenimiento",
        cascade="all, delete-orphan",
        order_by="desc(MantenimientoArchivo.created_at)",
    )

    @property
    def entidad_id(self) -> int | None:
        return self.id_trailer if self.id_trailer is not None else self.id_caja

    @property
    def entidad(self) -> dict[str, object]:
        if self.trailer is not None:
            return {
                "id": self.trailer.id_trailer,
                "etiqueta": self.trailer.numero_economico,
                "subtitulo": self.trailer.placas,
            }
        if self.caja is not None:
            return {
                "id": self.caja.id_caja,
                "etiqueta": self.caja.numero_economico or self.caja.placas,
                "subtitulo": self.caja.placas,
            }
        return {"id": 0, "etiqueta": "Sin recurso", "subtitulo": None}


class MantenimientoChecklistItem(Base):
    __tablename__ = "mantenimiento_checklist_items"

    id_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_mantenimiento: Mapped[int] = mapped_column(
        ForeignKey("mantenimientos.id_mantenimiento"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    completado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    mantenimiento = relationship("Mantenimiento", back_populates="checklist_items")
    evidencias = relationship(
        "MantenimientoChecklistEvidencia",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="desc(MantenimientoChecklistEvidencia.created_at)",
    )


class MantenimientoChecklistEvidencia(Base):
    __tablename__ = "mantenimiento_checklist_evidencias"

    id_checklist_evidencia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_item: Mapped[int] = mapped_column(
        ForeignKey("mantenimiento_checklist_items.id_item"),
        nullable=False,
    )
    id_archivo: Mapped[int] = mapped_column(ForeignKey("archivos_storage.id_archivo"), nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    item = relationship("MantenimientoChecklistItem", back_populates="evidencias")
    archivo = relationship("ArchivoStorage")
    usuario_creador = relationship("Usuario", foreign_keys=[created_by])


class MantenimientoArchivo(Base):
    __tablename__ = "mantenimiento_archivos"

    id_mantenimiento_archivo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_mantenimiento: Mapped[int] = mapped_column(
        ForeignKey("mantenimientos.id_mantenimiento"),
        nullable=False,
    )
    id_archivo: Mapped[int] = mapped_column(ForeignKey("archivos_storage.id_archivo"), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(String(30), nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    mantenimiento = relationship("Mantenimiento", back_populates="archivos")
    archivo = relationship("ArchivoStorage", back_populates="mantenimientos_archivos")
    usuario_creador = relationship("Usuario", foreign_keys=[created_by])


class Alerta(Base):
    __tablename__ = "alertas"

    id_alerta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo_alerta: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_id: Mapped[int] = mapped_column(Integer, nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    nivel: Mapped[str] = mapped_column(String(20), nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    requiere_notificacion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    notificada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    canal_notificacion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_notificacion: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class TelegramDestinatario(Base):
    __tablename__ = "telegram_destinatarios"

    id_destinatario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    chat_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    recibe_documentos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    recibe_mantenimiento: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    recibe_viajes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id_subscription: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    last_success_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    last_failure_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    usuario = relationship("Usuario", back_populates="push_subscriptions")


class Incidencia(Base):
    __tablename__ = "incidencias"

    id_incidencia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_viaje: Mapped[int] = mapped_column(ForeignKey("viajes.id_viaje"), nullable=False)
    id_operador: Mapped[int | None] = mapped_column(ForeignKey("operadores.id_operador"), nullable=True)
    tipo_incidencia: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    severidad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_incidencia: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    estatus: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ABIERTA", server_default="ABIERTA"
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    viaje = relationship("Viaje", back_populates="incidencias")
    operador = relationship("Operador", back_populates="incidencias")
    archivos = relationship("IncidenciaArchivo", back_populates="incidencia")


class IncidenciaArchivo(Base):
    __tablename__ = "incidencias_archivos"
    __table_args__ = (
        UniqueConstraint("id_incidencia", "id_archivo", name="uq_incidencia_archivo"),
    )

    id_incidencia_archivo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_incidencia: Mapped[int] = mapped_column(ForeignKey("incidencias.id_incidencia"), nullable=False)
    id_archivo: Mapped[int] = mapped_column(ForeignKey("archivos_storage.id_archivo"), nullable=False)
    comentario: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    incidencia = relationship("Incidencia", back_populates="archivos")
    archivo = relationship("ArchivoStorage", back_populates="incidencias_archivos")


class RespaldoControl(Base):
    __tablename__ = "respaldos"
    __table_args__ = (
        CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="ck_respaldos_size_bytes"),
        CheckConstraint("table_count IS NULL OR table_count >= 0", name="ck_respaldos_table_count"),
        CheckConstraint("row_count IS NULL OR row_count >= 0", name="ck_respaldos_row_count"),
        CheckConstraint(
            "format_version IS NULL OR format_version >= 1",
            name="ck_respaldos_format_version",
        ),
        CheckConstraint(
            "actor_source IN ('USER', 'SYSTEM', 'RECOVERY')",
            name="ck_respaldos_actor_source",
        ),
        CheckConstraint(
            "origen IN ('MANUAL', 'AUTOMATICO', 'PRE_RESTAURACION', 'IMPORTADO')",
            name="ck_respaldos_origen",
        ),
        CheckConstraint(
            "estado IN ('PENDIENTE', 'GENERANDO', 'VALIDANDO', 'DISPONIBLE', "
            "'FALLIDO', 'CORRUPTO', 'ELIMINADO')",
            name="ck_respaldos_estado",
        ),
        Index("ix_control_respaldos_created_at", "created_at"),
        Index("ix_control_respaldos_estado", "estado"),
        Index("ix_control_respaldos_origen", "origen"),
        {"schema": CONTROL_RESPALDO_SCHEMA},
    )

    id_respaldo: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    ruta_relativa: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    origen: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    format_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    application_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postgres_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True, unique=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    table_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    manifest_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actor_original_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_username_snapshot: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actor_role_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actor_nombre_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    actor_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_source: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    eliminado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OperacionRespaldoControl(Base):
    __tablename__ = "operaciones_respaldo"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('GENERACION', 'CARGA', 'VALIDACION', 'DESCARGA', 'RESTAURACION', "
            "'RECUPERACION', 'LIMPIEZA')",
            name="ck_operaciones_respaldo_tipo",
        ),
        CheckConstraint(
            "estado IN ('PENDIENTE', 'GENERANDO', 'VALIDANDO', 'RESPALDO_PREVIO', "
            "'BLOQUEANDO', 'RESTAURANDO', 'VERIFICANDO', 'RECUPERANDO', 'DESCARGANDO', "
            "'LIMPIANDO', 'EXITOSA', 'FALLIDA', 'FALLIDA_SIN_CAMBIOS', "
            "'FALLIDA_RECUPERADA', 'FALLIDA_CRITICA', 'CANCELADA', 'INTERRUMPIDA')",
            name="ck_operaciones_respaldo_estado",
        ),
        CheckConstraint(
            "actor_source IN ('USER', 'SYSTEM', 'RECOVERY')",
            name="ck_operaciones_respaldo_actor_source",
        ),
        CheckConstraint(
            "resultado_restauracion IS NULL OR resultado_restauracion IN "
            "('EXITOSA', 'FALLIDA_SIN_CAMBIOS', 'FALLIDA_RECUPERADA', 'FALLIDA_CRITICA')",
            name="ck_operaciones_resultado_restauracion",
        ),
        Index("ix_control_operaciones_created_at", "created_at"),
        Index("ix_control_operaciones_estado", "estado"),
        Index("ix_control_operaciones_heartbeat", "heartbeat_at"),
        Index(
            "uq_control_operacion_destructiva_activa",
            text("(1)"),
            unique=True,
            postgresql_where=text(
                "tipo IN ('RESTAURACION', 'RECUPERACION') AND estado IN "
                "('PENDIENTE', 'VALIDANDO', 'RESPALDO_PREVIO', 'BLOQUEANDO', "
                "'RESTAURANDO', 'VERIFICANDO', 'RECUPERANDO')"
            ),
        ),
        {"schema": CONTROL_RESPALDO_SCHEMA},
    )

    id_operacion: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    id_respaldo: Mapped[UUID | None] = mapped_column(
        ForeignKey("control_respaldo.respaldos.id_respaldo"), nullable=True
    )
    id_respaldo_seguridad: Mapped[UUID | None] = mapped_column(
        ForeignKey("control_respaldo.respaldos.id_respaldo"), nullable=True
    )
    correlation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True, default=uuid4
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(150), nullable=True, unique=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_original_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_username_snapshot: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actor_role_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actor_nombre_snapshot: Mapped[str | None] = mapped_column(String(200), nullable=True)
    actor_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_source: Mapped[str] = mapped_column(String(20), nullable=False)
    client_ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    resultado_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resultado_restauracion: Mapped[str | None] = mapped_column(String(30), nullable=True)


class ValidacionRespaldoControl(Base):
    __tablename__ = "validaciones_respaldo"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE', 'VALIDO', 'INVALIDO', 'EXPIRADO')",
            name="ck_validaciones_respaldo_estado",
        ),
        CheckConstraint(
            "format_version IS NULL OR format_version >= 1",
            name="ck_validaciones_format_version",
        ),
        Index("ix_control_validaciones_created_at", "created_at"),
        Index("ix_control_validaciones_estado", "estado"),
        Index("ix_control_validaciones_expires_at", "expires_at"),
        {"schema": CONTROL_RESPALDO_SCHEMA},
    )

    id_validacion: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    id_respaldo: Mapped[UUID] = mapped_column(
        ForeignKey("control_respaldo.respaldos.id_respaldo"), nullable=False
    )
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    format_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resultado_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actor_original_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_username_snapshot: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actor_role_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actor_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConfirmacionRestauracionControl(Base):
    __tablename__ = "confirmaciones_restauracion"
    __table_args__ = (
        Index("ix_control_confirmaciones_expires_at", "expires_at"),
        {"schema": CONTROL_RESPALDO_SCHEMA},
    )

    id_confirmacion: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    id_respaldo: Mapped[UUID] = mapped_column(
        ForeignKey("control_respaldo.respaldos.id_respaldo"), nullable=False
    )
    actor_original_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_username_snapshot: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actor_role_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    confirmation_phrase_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EstadoSistemaControl(Base):
    __tablename__ = "estado_sistema"
    __table_args__ = (
        CheckConstraint(
            "clave = 'MANTENIMIENTO_RESTAURACION'",
            name="ck_estado_sistema_clave",
        ),
        {"schema": CONTROL_RESPALDO_SCHEMA},
    )

    clave: Mapped[str] = mapped_column(String, primary_key=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    id_operacion: Mapped[UUID | None] = mapped_column(
        ForeignKey("control_respaldo.operaciones_respaldo.id_operacion"), nullable=True
    )
    mensaje_publico: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class WorkerRespaldoControl(Base):
    __tablename__ = "workers_respaldo"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('ACTIVO', 'OCUPADO', 'INACTIVO', 'ERROR')",
            name="ck_workers_respaldo_estado",
        ),
        Index("ix_control_workers_last_heartbeat", "last_heartbeat_at"),
        Index("ix_control_workers_estado", "estado"),
        {"schema": CONTROL_RESPALDO_SCHEMA},
    )

    worker_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    application_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postgres_tools_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    id_operacion_actual: Mapped[UUID | None] = mapped_column(
        ForeignKey("control_respaldo.operaciones_respaldo.id_operacion"), nullable=True
    )


class TicketDescargaControl(Base):
    __tablename__ = "tickets_descarga"
    __table_args__ = (
        Index("ix_control_tickets_expires_at", "expires_at"),
        {"schema": CONTROL_RESPALDO_SCHEMA},
    )

    id_ticket: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    id_respaldo: Mapped[UUID] = mapped_column(
        ForeignKey("control_respaldo.respaldos.id_respaldo"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    actor_original_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_username_snapshot: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
