import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_refresh_renueva_sesion_y_no_funciona_como_access_token(
    client: AsyncClient,
    supervisor_token: str,
):
    login = await client.post(
        "/api/v1/auth/login",
        json={"codigo_empleado": "SUP-001", "password": "test123"},
    )

    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh.status_code == 200
    renewed = refresh.json()
    assert renewed["access_token"]
    assert renewed["refresh_token"]

    profile = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {renewed['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["rol"] == "SUPERVISOR"

    rejected = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert rejected.status_code == 401
