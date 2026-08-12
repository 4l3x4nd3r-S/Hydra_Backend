import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_local_db():
    LOCAL_URL = "postgresql+asyncpg://postgres:alexander123@localhost:5432/hydra_2"
    try:
        engine = create_async_engine(LOCAL_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM reclamos_historicos"))
            count = result.scalar()
            print(f"Local reclamos_historicos count: {count}")
        await engine.dispose()
    except Exception as e:
        print(f"Error checking local DB: {e}")

if __name__ == "__main__":
    asyncio.run(check_local_db())
