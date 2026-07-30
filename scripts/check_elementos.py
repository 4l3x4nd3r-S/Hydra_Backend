import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.elemento_red import ElementoRed

async def clean_duplicates():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ElementoRed))
        elementos = res.scalars().all()
        coords_map = {}
        for el in elementos:
            # We round to 6 decimals for comparison
            if el.latitud is None or el.longitud is None:
                continue
            key = f"{el.latitud:.6f},{el.longitud:.6f},{el.tipo}"
            if key in coords_map:
                coords_map[key].append(el.id)
            else:
                coords_map[key] = [el.id]
                
        ids_to_delete = []
        for k, ids in coords_map.items():
            if len(ids) > 1:
                # Keep the first one (lowest ID), delete the rest
                ids.sort()
                ids_to_delete.extend(ids[1:])
                
        if ids_to_delete:
            print(f"Borrando {len(ids_to_delete)} elementos duplicados en elementos_red...")
            await db.execute(delete(ElementoRed).where(ElementoRed.id.in_(ids_to_delete)))
            await db.commit()
            print("Duplicados eliminados exitosamente.")
        else:
            print("No se encontraron duplicados.")

if __name__ == "__main__":
    asyncio.run(clean_duplicates())
