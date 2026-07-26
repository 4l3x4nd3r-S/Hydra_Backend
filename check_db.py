import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.punto_presion import PuntoPresion

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(PuntoPresion.codigo_punto).limit(15))
        print(result.scalars().all())

if __name__ == "__main__":
    asyncio.run(main())
