import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.orden_servicio import OrdenServicio
from app.models.reclamo import Reclamo
from app.models.cuadrilla import Cuadrilla
from app.models.usuario import Usuario, RolUsuario
from app.services.orden_servicio_service import OrdenServicioService


@pytest_asyncio.fixture
async def setup_datos(db_session: AsyncSession):
    await db_session.execute(
        text(
            """
            INSERT INTO usuarios (id, codigo_empleado, nombre, password_hash, rol, activo)
            VALUES (1, 'SUP-001', 'Supervisor Test', 'hash', 'SUPERVISOR', true)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO reclamos (id, formato, codigo_solicitud, canal_entrada, tipo_problema,
                estado, descripcion, direccion, fecha_registro)
            VALUES (10, 'F-001', 'CS-001', 'TELEFONO', 'FUGA', 'PENDIENTE', 'Fuga visible', 'Av. Peru 123', now())
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO cuadrillas (id, codigo_grupo, especialidad)
            VALUES (4, 'Grupo #4', 'Agua')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.flush()


@pytest.mark.asyncio
async def test_crear_os_desde_reclamo_exitoso(db_session: AsyncSession, setup_datos):
    from app.models.usuario import Usuario

    actor_result = await db_session.execute(text("SELECT * FROM usuarios WHERE id = 1"))
    actor_row = actor_result.mappings().first()
    actor = Usuario(
        id=actor_row["id"],
        codigo_empleado=actor_row["codigo_empleado"],
        nombre=actor_row["nombre"],
        password_hash=actor_row["password_hash"],
        rol=RolUsuario(actor_row["rol"]),
        activo=actor_row["activo"],
    )
    actor_obj = actor

    service = OrdenServicioService(db_session)
    ot = await service.crear_desde_reclamo(
        reclamo_id=10,
        cuadrilla_id=4,
        supervisor_id=1,
        fecha_programacion=None,
        actor=actor_obj,
    )
    await db_session.commit()

    assert ot.id is not None
    assert ot.numero_orden is not None
    assert ot.numero_orden.startswith("OS-")
    assert ot.reclamo_id == 10
    assert ot.cuadrilla_id == 4
    assert ot.supervisor_id == 1
    assert ot.estado_orden == "ASIGNADO"

    reclamo_result = await db_session.execute(
        text("SELECT estado FROM reclamos WHERE id = 10")
    )
    assert reclamo_result.scalar_one() == "ASIGNADO"

    auditoria_result = await db_session.execute(
        text("SELECT accion FROM auditoria_eventos WHERE entidad = 'orden_servicio'")
    )
    assert auditoria_result.scalar_one() == "OS_CREADA"

    secuencia_result = await db_session.execute(
        text("SELECT count(*) FROM os_secuencia WHERE fecha = :fecha"),
        {"fecha": date.today()},
    )
    assert secuencia_result.scalar_one() == 1


@pytest.mark.asyncio
async def test_crear_os_reclamo_inexistente(db_session: AsyncSession, setup_datos):
    from app.models.usuario import Usuario

    actor_result = await db_session.execute(text("SELECT * FROM usuarios WHERE id = 1"))
    row = actor_result.mappings().first()
    actor = Usuario(
        id=row["id"],
        codigo_empleado=row["codigo_empleado"],
        nombre=row["nombre"],
        password_hash=row["password_hash"],
        rol=RolUsuario(row["rol"]),
        activo=row["activo"],
    )

    service = OrdenServicioService(db_session)
    with pytest.raises(ValueError, match="Reclamo no encontrado"):
        await service.crear_desde_reclamo(
            reclamo_id=999,
            cuadrilla_id=4,
            supervisor_id=1,
            fecha_programacion=None,
            actor=actor,
        )


@pytest.mark.asyncio
async def test_crear_os_cuadrilla_inexistente(db_session: AsyncSession, setup_datos):
    from app.models.usuario import Usuario

    actor_result = await db_session.execute(text("SELECT * FROM usuarios WHERE id = 1"))
    row = actor_result.mappings().first()
    actor = Usuario(
        id=row["id"],
        codigo_empleado=row["codigo_empleado"],
        nombre=row["nombre"],
        password_hash=row["password_hash"],
        rol=RolUsuario(row["rol"]),
        activo=row["activo"],
    )

    service = OrdenServicioService(db_session)
    with pytest.raises(ValueError, match="Cuadrilla no encontrada"):
        await service.crear_desde_reclamo(
            reclamo_id=10,
            cuadrilla_id=999,
            supervisor_id=1,
            fecha_programacion=None,
            actor=actor,
        )


@pytest.mark.asyncio
async def test_crear_os_reclamo_con_os_activa(db_session: AsyncSession, setup_datos):
    from app.models.usuario import Usuario

    actor_result = await db_session.execute(text("SELECT * FROM usuarios WHERE id = 1"))
    row = actor_result.mappings().first()
    actor = Usuario(
        id=row["id"],
        codigo_empleado=row["codigo_empleado"],
        nombre=row["nombre"],
        password_hash=row["password_hash"],
        rol=RolUsuario(row["rol"]),
        activo=row["activo"],
    )

    service = OrdenServicioService(db_session)
    await service.crear_desde_reclamo(
        reclamo_id=10,
        cuadrilla_id=4,
        supervisor_id=1,
        fecha_programacion=None,
        actor=actor,
    )
    await db_session.commit()

    with pytest.raises(ValueError, match="El reclamo ya tiene una O.S. activa"):
        await service.crear_desde_reclamo(
            reclamo_id=10,
            cuadrilla_id=4,
            supervisor_id=1,
            fecha_programacion=None,
            actor=actor,
        )


@pytest.mark.asyncio
async def test_numeracion_correlativa_diaria(db_session: AsyncSession, setup_datos):
    from app.models.usuario import Usuario

    actor_result = await db_session.execute(text("SELECT * FROM usuarios WHERE id = 1"))
    row = actor_result.mappings().first()
    actor = Usuario(
        id=row["id"],
        codigo_empleado=row["codigo_empleado"],
        nombre=row["nombre"],
        password_hash=row["password_hash"],
        rol=RolUsuario(row["rol"]),
        activo=row["activo"],
    )

    await db_session.execute(
        text(
            """
            INSERT INTO reclamos (id, formato, codigo_solicitud, canal_entrada, tipo_problema,
                estado, descripcion, direccion, fecha_registro)
            VALUES (11, 'F-002', 'CS-002', 'TELEFONO', 'FUGA', 'PENDIENTE', 'Otra fuga', 'Av. Lima 456', now())
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.flush()

    service = OrdenServicioService(db_session)

    ot1 = await service.crear_desde_reclamo(
        reclamo_id=10,
        cuadrilla_id=4,
        supervisor_id=1,
        fecha_programacion=None,
        actor=actor,
    )
    await db_session.commit()

    ot2 = await service.crear_desde_reclamo(
        reclamo_id=11,
        cuadrilla_id=4,
        supervisor_id=1,
        fecha_programacion=None,
        actor=actor,
    )
    await db_session.commit()

    assert ot1.numero_orden != ot2.numero_orden
    assert ot2.numero_orden.endswith("0002")
