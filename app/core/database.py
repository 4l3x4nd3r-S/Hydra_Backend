from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    # Render/Supabase pueden cerrar conexiones inactivas. El pre-ping descarta
    # una conexión vencida antes de entregársela a una petición de la API.
    pool_pre_ping=True,
    # Evita conservar conexiones durante demasiado tiempo en procesos activos.
    pool_recycle=300,
    pool_timeout=30,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
