import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def update_canales():
    async with AsyncSessionLocal() as session:
        await session.execute(text("UPDATE reclamos SET canal_entrada = 'Presencial' WHERE canal_entrada = 'Presencial (Módulo Comercial)'"))
        await session.execute(text("UPDATE reclamos SET canal_entrada = 'Call Center' WHERE canal_entrada = 'Call Center (3er Piso)'"))
        await session.commit()
        print('Canales actualizados en la base de datos.')

if __name__ == "__main__":
    asyncio.run(update_canales())
