import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.orden_servicio import OrdenServicio

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(OrdenServicio))
        ordenes = res.scalars().all()
        for o in ordenes:
            if o.numero_orden == '0000029' or o.id == 29:
                print(f"FOUND: ID={o.id}, N={o.numero_orden}, Estado={o.estado_orden}")
        print("Total ordenes:", len(ordenes))
        print("IDs presentes:", [o.id for o in ordenes])

if __name__ == "__main__":
    asyncio.run(check())
