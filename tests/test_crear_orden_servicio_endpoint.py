import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


@pytest.mark.asyncio
async def test_post_ots_crea_y_marca_reclamo(client: AsyncClient, auth_headers, db_session: AsyncSession):
    await db_session.execute(
        text(
            """
            INSERT INTO reclamos (id, formato, codigo_solicitud, canal_entrada, tipo_problema,
                estado, descripcion, direccion, fecha_registro)
            VALUES (20, 'Formato 1', '00020', 'PRESENCIAL', 'ROTURA', 'PENDIENTE', 'Desc', 'Calle 1', now())
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO cuadrillas (id, codigo_grupo, especialidad)
            VALUES (5, 'Grupo #5', 'Agua')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/supervisor/ordenes-servicio",
        json={
            "reclamo_id": 20,
            "cuadrilla_id": 5,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reclamo_id"] == 20
    assert data["cuadrilla_id"] == 5
    assert data["estado_orden"] == "ASIGNADO"
    assert data["numero_orden"] is not None
    assert len(data["numero_orden"]) == 7
    assert data["numero_orden"].isdigit()
    assert data["reclamo"] is not None
    assert data["reclamo"]["estado"] == "ASIGNADO"


@pytest.mark.asyncio
async def test_post_ots_reclamo_con_os_activa_rechaza(client: AsyncClient, auth_headers, db_session: AsyncSession):
    await db_session.execute(
        text(
            """
            INSERT INTO reclamos (id, formato, codigo_solicitud, canal_entrada, tipo_problema,
                estado, descripcion, direccion, fecha_registro)
            VALUES (21, 'Formato 1', '00021', 'PRESENCIAL', 'ROTURA', 'PENDIENTE', 'Desc', 'Calle 2', now())
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.execute(
        text(
            """
            INSERT INTO cuadrillas (id, codigo_grupo, especialidad)
            VALUES (6, 'Grupo #6', 'Agua')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await db_session.flush()

    await client.post(
        "/api/v1/supervisor/ordenes-servicio",
        json={"reclamo_id": 21, "cuadrilla_id": 6},
        headers=auth_headers,
    )

    response = await client.post(
        "/api/v1/supervisor/ordenes-servicio",
        json={"reclamo_id": 21, "cuadrilla_id": 6},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "ya tiene una O.S. activa" in response.json()["detail"]


@pytest.mark.asyncio
async def test_post_ots_sin_autenticacion_rechaza(client: AsyncClient):
    response = await client.post(
        "/api/v1/supervisor/ordenes-servicio",
        json={"reclamo_id": 1, "cuadrilla_id": 1},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_post_ots_reclamo_inexistente(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/supervisor/ordenes-servicio",
        json={"reclamo_id": 99999, "cuadrilla_id": 1},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Reclamo no encontrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_post_ots_reclamo_id_obligatorio(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/supervisor/ordenes-servicio",
        json={"cuadrilla_id": 1},
        headers=auth_headers,
    )
    assert response.status_code == 422
