import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.orden_servicio import OrdenServicio

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(OrdenServicio).options(selectinload(OrdenServicio.reclamo)))
        for o in res.scalars().all():
            r = o.reclamo
            desc = r.descripcion if r else "NO RECLAMO"
            print(f"OS ID {o.id} | N {o.numero_orden} | Desc: '{desc}' | Estado: {o.estado_orden}")

if __name__ == "__main__":
    asyncio.run(check())
