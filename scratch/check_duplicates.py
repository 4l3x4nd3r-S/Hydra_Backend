import asyncio
from sqlalchemy import select, delete, update
from app.core.database import AsyncSessionLocal
from app.models.sector import Sector
from app.models.elemento_red import ElementoRed
from app.models.punto_presion import PuntoPresion

async def main():
    async with AsyncSessionLocal() as session:
        # Get all sectors ordered by ID
        result = await session.execute(select(Sector).order_by(Sector.id))
        sectores = result.scalars().all()
        
        seen_names = {}
        duplicates = []
        for s in sectores:
            if s.nombre in seen_names:
                duplicates.append((s, seen_names[s.nombre]))
            else:
                seen_names[s.nombre] = s
        
        print(f"Found {len(duplicates)} duplicates")
        for dup, original in duplicates:
            # Check usages
            red_count = await session.execute(select(ElementoRed).where(ElementoRed.sector_id == dup.id))
            presion_count = await session.execute(select(PuntoPresion).where(PuntoPresion.sector_id == dup.id))
            print(f"Duplicate {dup.nombre} (ID: {dup.id}) has {len(red_count.scalars().all())} ElementoRed and {len(presion_count.scalars().all())} PuntoPresion. Original ID: {original.id}")

            # Reassign
            await session.execute(update(ElementoRed).where(ElementoRed.sector_id == dup.id).values(sector_id=original.id))
            await session.execute(update(PuntoPresion).where(PuntoPresion.sector_id == dup.id).values(sector_id=original.id))
            
            # Delete
            await session.execute(delete(Sector).where(Sector.id == dup.id))
            print(f"Deleted duplicate ID {dup.id}")
            
        await session.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
