import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        try:
            # Drop constraints
            print("Dropping constraints...")
            await session.execute(text("ALTER TABLE elementos_red DROP CONSTRAINT elementos_red_sector_id_fkey"))
            await session.execute(text("ALTER TABLE puntos_presion DROP CONSTRAINT puntos_presion_sector_id_fkey"))
            await session.execute(text("ALTER TABLE registros_presion DROP CONSTRAINT registros_presion_punto_presion_id_fkey"))
            
            print("Shifting sectores IDs...")
            await session.execute(text("UPDATE sectores SET id = id - 1"))
            
            print("Shifting puntos_presion IDs...")
            await session.execute(text("UPDATE puntos_presion SET id = id - 1"))
            
            print("Updating foreign keys...")
            await session.execute(text("UPDATE elementos_red SET sector_id = sector_id - 1 WHERE sector_id IS NOT NULL"))
            await session.execute(text("UPDATE puntos_presion SET sector_id = sector_id - 1 WHERE sector_id IS NOT NULL"))
            await session.execute(text("UPDATE registros_presion SET punto_presion_id = punto_presion_id - 1 WHERE punto_presion_id IS NOT NULL"))
            
            print("Re-adding constraints...")
            await session.execute(text("ALTER TABLE elementos_red ADD CONSTRAINT elementos_red_sector_id_fkey FOREIGN KEY (sector_id) REFERENCES sectores(id)"))
            await session.execute(text("ALTER TABLE puntos_presion ADD CONSTRAINT puntos_presion_sector_id_fkey FOREIGN KEY (sector_id) REFERENCES sectores(id)"))
            await session.execute(text("ALTER TABLE registros_presion ADD CONSTRAINT registros_presion_punto_presion_id_fkey FOREIGN KEY (punto_presion_id) REFERENCES puntos_presion(id) ON DELETE CASCADE"))
            
            print("Resetting sequences...")
            await session.execute(text("SELECT setval('sectores_id_seq', (SELECT COALESCE(MAX(id), 1) FROM sectores))"))
            await session.execute(text("SELECT setval('puntos_presion_id_seq', (SELECT COALESCE(MAX(id), 1) FROM puntos_presion))"))
            
            await session.commit()
            print("Done shifting IDs")
        except Exception as e:
            await session.rollback()
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
