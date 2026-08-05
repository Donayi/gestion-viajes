import pytest

from app.crud.crud_viajes import (
    caja_disponible_para_asignacion,
    create_asignacion_viaje,
    get_cajas_disponibles,
    get_disponibilidad_resumen,
    get_trailers_disponibles,
    trailer_disponible_para_asignacion,
)
from app.models.models import (
    AsignacionViaje,
    Caja,
    CatalogoEstatusViaje,
    Cliente,
    Mantenimiento,
    Operador,
    Rol,
    Trailer,
    Usuario,
    Viaje,
)
from app.schemas.viaje import ViajeAsignacionCreate


@pytest.fixture
def escenario_operativo(db_session):
    rol = Rol(nombre="OPERADOR_TEST", descripcion="Rol aislado de pruebas")
    usuario = Usuario(
        username="operador_test",
        password_hash="not-used",
        nombre="Operador",
        apellido="Prueba",
        rol=rol,
    )
    operador = Operador(alias="Operador prueba", usuario=usuario)
    cliente = Cliente(nombre_razon_social="Cliente prueba")
    creado = CatalogoEstatusViaje(
        clave="CREADO",
        nombre="Creado",
        orden_flujo=1,
        es_terminal=False,
    )
    asignado = CatalogoEstatusViaje(
        clave="ASIGNADO",
        nombre="Asignado",
        orden_flujo=2,
        es_terminal=False,
    )
    trailer = Trailer(numero_economico="T-TEST-001", placas="TR-TEST-001")
    caja = Caja(numero_economico="C-TEST-001", placas="CJ-TEST-001")

    db_session.add_all([rol, usuario, operador, cliente, creado, asignado, trailer, caja])
    db_session.flush()

    viaje = Viaje(
        folio="VIAJE-TEST-001",
        id_cliente=cliente.id_cliente,
        lugar_inicio="Origen prueba",
        lugar_destino="Destino prueba",
        id_estatus_actual=creado.id_estatus,
    )
    db_session.add(viaje)
    db_session.flush()

    return {
        "operador": operador,
        "trailer": trailer,
        "caja": caja,
        "viaje": viaje,
        "creado": creado,
        "asignado": asignado,
    }


def _recurso_en_resumen(resumen, grupo, id_field, recurso_id):
    return next(item for item in resumen[grupo] if item[id_field] == recurso_id)


def test_trailer_libre_es_asignable_y_aparece_disponible(
    db_session, escenario_operativo
):
    trailer = escenario_operativo["trailer"]

    assert trailer_disponible_para_asignacion(db_session, trailer.id_trailer)
    assert trailer.id_trailer in {
        item.id_trailer for item in get_trailers_disponibles(db_session)
    }

    item = _recurso_en_resumen(
        get_disponibilidad_resumen(db_session),
        "trailers",
        "id_trailer",
        trailer.id_trailer,
    )
    assert item["disponible"] is True
    assert item["motivo_no_disponible"] is None


def test_caja_libre_es_asignable_y_aparece_disponible(db_session, escenario_operativo):
    caja = escenario_operativo["caja"]

    assert caja_disponible_para_asignacion(db_session, caja.id_caja)
    assert caja.id_caja in {item.id_caja for item in get_cajas_disponibles(db_session)}

    item = _recurso_en_resumen(
        get_disponibilidad_resumen(db_session),
        "cajas",
        "id_caja",
        caja.id_caja,
    )
    assert item["disponible"] is True
    assert item["motivo_no_disponible"] is None


def test_recursos_libres_permiten_asignacion_persistida_y_sesion_utilizable(
    db_session, escenario_operativo
):
    viaje = escenario_operativo["viaje"]
    operador = escenario_operativo["operador"]
    trailer = escenario_operativo["trailer"]
    caja = escenario_operativo["caja"]
    asignado = escenario_operativo["asignado"]

    asignacion = create_asignacion_viaje(
        db_session,
        viaje,
        ViajeAsignacionCreate(
            id_operador=operador.id_operador,
            id_trailer=trailer.id_trailer,
            id_caja=caja.id_caja,
            motivo="Asignación exitosa de prueba",
        ),
    )
    asignacion_id = asignacion.id_asignacion
    viaje_id = viaje.id_viaje

    db_session.expire_all()
    asignacion_persistida = db_session.get(AsignacionViaje, asignacion_id)
    viaje_persistido = db_session.get(Viaje, viaje_id)

    assert asignacion_persistida is not None
    assert asignacion_persistida.activo is True
    assert asignacion_persistida.id_viaje == viaje_id
    assert asignacion_persistida.id_operador == operador.id_operador
    assert asignacion_persistida.id_trailer == trailer.id_trailer
    assert asignacion_persistida.id_caja == caja.id_caja

    assert viaje_persistido is not None
    assert viaje_persistido.id_estatus_actual == asignado.id_estatus
    assert viaje_persistido.estatus_actual.clave == "ASIGNADO"
    assert viaje_persistido.id_operador_actual == operador.id_operador
    assert viaje_persistido.id_trailer_actual == trailer.id_trailer
    assert viaje_persistido.id_caja_actual == caja.id_caja

    assert db_session.query(AsignacionViaje).filter_by(id_viaje=viaje_id).count() == 1
    assert db_session.query(Viaje).filter_by(id_viaje=viaje_id).one().folio == "VIAJE-TEST-001"


@pytest.mark.parametrize("entidad_tipo", ["TRAILER", "CAJA"])
@pytest.mark.parametrize("estatus_mantenimiento", ["ABIERTO", "EN_PROCESO"])
def test_mantenimiento_activo_bloquea_asignacion_y_conserva_consistencia(
    db_session,
    escenario_operativo,
    entidad_tipo,
    estatus_mantenimiento,
):
    viaje = escenario_operativo["viaje"]
    operador = escenario_operativo["operador"]
    trailer = escenario_operativo["trailer"]
    caja = escenario_operativo["caja"]
    creado = escenario_operativo["creado"]

    mantenimiento = Mantenimiento(
        entidad_tipo=entidad_tipo,
        id_trailer=trailer.id_trailer if entidad_tipo == "TRAILER" else None,
        id_caja=caja.id_caja if entidad_tipo == "CAJA" else None,
        tipo_mantenimiento="PREVENTIVO",
        estatus=estatus_mantenimiento,
        descripcion="Mantenimiento activo de prueba",
    )
    db_session.add(mantenimiento)
    db_session.flush()

    payload = ViajeAsignacionCreate(
        id_operador=operador.id_operador,
        id_trailer=trailer.id_trailer,
        id_caja=caja.id_caja,
        motivo="Prueba de invariante",
    )
    expected_message = (
        "El tráiler está en mantenimiento y no puede asignarse"
        if entidad_tipo == "TRAILER"
        else "La caja está en mantenimiento y no puede asignarse"
    )

    with pytest.raises(ValueError, match=expected_message):
        create_asignacion_viaje(db_session, viaje, payload)

    db_session.expire_all()
    viaje_persistido = db_session.get(Viaje, viaje.id_viaje)
    assert db_session.query(AsignacionViaje).count() == 0
    assert viaje_persistido is not None
    assert viaje_persistido.id_estatus_actual == creado.id_estatus
    assert viaje_persistido.id_operador_actual is None
    assert viaje_persistido.id_trailer_actual is None
    assert viaje_persistido.id_caja_actual is None

    resumen = get_disponibilidad_resumen(db_session)
    if entidad_tipo == "TRAILER":
        assert trailer_disponible_para_asignacion(db_session, trailer.id_trailer) is False
        assert trailer.id_trailer not in {
            item.id_trailer for item in get_trailers_disponibles(db_session)
        }
        item = _recurso_en_resumen(
            resumen, "trailers", "id_trailer", trailer.id_trailer
        )
    else:
        assert caja_disponible_para_asignacion(db_session, caja.id_caja) is False
        assert caja.id_caja not in {
            item.id_caja for item in get_cajas_disponibles(db_session)
        }
        item = _recurso_en_resumen(resumen, "cajas", "id_caja", caja.id_caja)

    assert item["disponible"] is False
    assert item["motivo_no_disponible"] == "En mantenimiento"
