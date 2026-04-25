from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


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


class Operador(Base):
    __tablename__ = "operadores"

    id_operador: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=False, unique=True)
    alias: Mapped[str] = mapped_column(String(150), nullable=False)
    numero_licencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
    id_cliente: Mapped[int] = mapped_column(ForeignKey("clientes.id_cliente"), nullable=False)

    lugar_inicio: Mapped[str] = mapped_column(String(255), nullable=False)
    lugar_destino: Mapped[str] = mapped_column(String(255), nullable=False)
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
    fecha_inicio: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    fecha_llegada: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    fecha_entrega: Mapped[Date | None] = mapped_column(Date, nullable=True)
    hora_entrega: Mapped[Time | None] = mapped_column(Time, nullable=True)

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
    kilometraje: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    nivel_diesel: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
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
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    tipo_documento = relationship("TipoDocumento", back_populates="documentos")
    operador = relationship("Operador", back_populates="documentos")
    trailer = relationship("Trailer", back_populates="documentos")
    caja = relationship("Caja", back_populates="documentos")
    viaje = relationship("Viaje", back_populates="documentos")
    archivo = relationship("ArchivoStorage", back_populates="documentos")
    usuario_subio = relationship("Usuario", back_populates="documentos_subidos")


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
    id_tipo_evidencia: Mapped[int] = mapped_column(ForeignKey("tipos_evidencia.id_tipo_evidencia"), nullable=False)
    id_operador: Mapped[int | None] = mapped_column(ForeignKey("operadores.id_operador"), nullable=True)
    id_archivo: Mapped[int] = mapped_column(ForeignKey("archivos_storage.id_archivo"), nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_captura: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    latitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    viaje = relationship("Viaje", back_populates="evidencias")
    tipo_evidencia = relationship("TipoEvidencia", back_populates="evidencias")
    operador = relationship("Operador", back_populates="evidencias")
    archivo = relationship("ArchivoStorage", back_populates="evidencias")


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
