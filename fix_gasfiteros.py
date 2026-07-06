import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from app.models.usuario import Usuario, CargoUsuario
from dotenv import load_dotenv

load_dotenv()

async def main():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL is not set.")
        return

    print(f"Connecting to database...")
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        print("Updating users with cargo GASFITERO_PRINCIPAL -> GASFITERO...")
        stmt = (
            update(Usuario)
            .where(Usuario.cargo == CargoUsuario.GASFITERO_PRINCIPAL)
            .values(cargo=CargoUsuario.GASFITERO)
        )
        result = await session.execute(stmt)
        await session.commit()
        print(f"Database updated successfully. Rows affected: {result.rowcount}")

if __name__ == "__main__":
    asyncio.run(main())
