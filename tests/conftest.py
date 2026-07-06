import os
import sys
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/hydra_test",
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def supervisor_token(client: AsyncClient, db_session: AsyncSession) -> str:
    from app.core.security import hash_password
    from sqlalchemy import text

    await db_session.execute(
        text(
            """
            INSERT INTO usuarios (id, codigo_empleado, nombre, password_hash, rol, activo)
            VALUES (1, 'SUP-001', 'Supervisor Test', :phash, 'SUPERVISOR', true)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"phash": hash_password("test123")},
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"codigo_empleado": "SUP-001", "password": "test123"},
    )
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def auth_headers(supervisor_token: str) -> dict:
    return {"Authorization": f"Bearer {supervisor_token}"}
