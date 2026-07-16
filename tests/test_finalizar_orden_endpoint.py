import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_finalizar_os_precarga_cuadrilla_y_construye_snapshot(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
):
    await db_session.execute(
        text(
            """
            INSERT INTO usuarios (
                id, codigo_empleado, nombre, password_hash, rol, cargo, area, activo
            ) VALUES (
                902, 'GAS-902', 'Lider Snapshot', 'hash', 'GASFITERO',
                'GASFITERO', 'MANTENIMIENTO', true
            )
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO reclamos (
                id, formato, codigo_solicitud, canal_entrada, tipo_problema,
                estado, descripcion, direccion, fecha_registro
            ) VALUES (
                901, 'Formato 1', '00901', 'PRESENCIAL', 'B8',
                'ASIGNADO', 'Prueba de finalizacion', 'Av. Prueba 901', now()
            )
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO cuadrillas (id, codigo_grupo, especialidad)
            VALUES (901, 'Cuadrilla 901', 'Agua')
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO cuadrillas_personal (
                cuadrilla_id, usuario_id, rol_en_cuadrilla
            ) VALUES (901, 902, 'LIDER')
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO ordenes_servicio (
                id, numero_orden, reclamo_id, supervisor_id, cuadrilla_id,
                estado_orden, fecha_ejecucion_inicio
            ) VALUES (
                901, '9000901', 901, 1, 901,
                'EN_PROCESO', now()
            )
            """
        )
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/ordenes-servicio/901/finalizar",
        headers=auth_headers,
        json={
            "observaciones_gasfitero": "Finalizada desde cola offline",
            "fotos_problema_urls": [],
            "fotos_solucion_urls": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["estado_orden"] == "COMPLETADO"
    assert data["cuadrilla"]["codigo_grupo"] == "Cuadrilla 901"
    assert data["cuadrilla"]["lider"]["nombre"] == "Lider Snapshot"

    snapshot = await db_session.execute(
        text(
            """
            SELECT cuadrilla_snapshot
            FROM ordenes_servicio
            WHERE id = 901
            """
        )
    )
    assert snapshot.scalar_one()["lider"]["id"] == 902

    retry_response = await client.post(
        "/api/v1/ordenes-servicio/901/finalizar",
        headers=auth_headers,
        json={"observaciones_gasfitero": "Reintento de la cola offline"},
    )

    assert retry_response.status_code == 200
    retry_data = retry_response.json()
    assert retry_data["estado_orden"] == "COMPLETADO"
    assert retry_data["observaciones_gasfitero"] == "Finalizada desde cola offline"

    late_start_retry = await client.post(
        "/api/v1/ordenes-servicio/901/iniciar",
        headers=auth_headers,
    )
    assert late_start_retry.status_code == 200
    assert late_start_retry.json()["estado_orden"] == "COMPLETADO"
