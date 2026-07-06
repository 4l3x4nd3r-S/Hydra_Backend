import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.usuario import Usuario
from app.core.security import hash_password

async def fix_passwords():
    async with AsyncSessionLocal() as db:
        # Update SUP001
        new_hash = hash_password("SUP001")
        await db.execute(
            update(Usuario)
            .where(Usuario.codigo_empleado == "SUP001")
            .values(password_hash=new_hash)
        )
        await db.commit()
        print("Contraseña de SUP001 actualizada a SUP001")

if __name__ == "__main__":
    asyncio.run(fix_passwords())
