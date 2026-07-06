import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.usuario import Usuario, RolUsuario, CargoUsuario, AreaUsuario
from app.core.security import hash_password

usuarios_data = [
    {"codigo": "SUP001", "nombre": "Supervisor1", "rol": RolUsuario.SUPERVISOR, "cargo": None, "area": None},
    {"codigo": "DIS001", "nombre": "Cristobal Castillo Cahuana", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.OPERADOR_RETROEXCAVADORA, "area": AreaUsuario.DISTRIBUCION},
    {"codigo": "DIS002", "nombre": "Saul Diaz Barrios", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.DISTRIBUCION},
    {"codigo": "DIS005", "nombre": "Victor Guerra Velasque", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.DISTRIBUCION},
    {"codigo": "DIS007", "nombre": "Fernando", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.DISTRIBUCION},
    {"codigo": "DIS008", "nombre": "Ormeño", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.DISTRIBUCION},
    {"codigo": "MAN001", "nombre": "Teodoro Condori Huaman", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.CHOFER_CAMIONETA, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN002", "nombre": "Alberto Vargas Peralta", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN003", "nombre": "Daniel Huesembe Ventura", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN004", "nombre": "Manuel Cardenas Campana", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN005", "nombre": "Ernesto Caceres Huacac", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN006", "nombre": "Juan David Quispe Guerra", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN007", "nombre": "Juan Pablo Rodriguez Chapiama", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN008", "nombre": "Raul Coral Murrieta", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN009", "nombre": "Mario Osorio Postigo", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN010", "nombre": "Jonas Huaman Ccallahuallpa", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN011", "nombre": "Ricardo Conza Singuña", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "MAN012", "nombre": "Yordy Dancuart Guerra", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO, "area": AreaUsuario.MANTENIMIENTO},
    {"codigo": "DIS004", "nombre": "Alejandro Salgado Quispe", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO_PRINCIPAL, "area": AreaUsuario.DISTRIBUCION},
    {"codigo": "DIS003", "nombre": "Esteban Chavez Zegarra", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO_PRINCIPAL, "area": AreaUsuario.DISTRIBUCION},
    {"codigo": "DIS006", "nombre": "Emanuel Addiso Joseph Inuma Osorio", "rol": RolUsuario.GASFITERO, "cargo": CargoUsuario.GASFITERO_PRINCIPAL, "area": AreaUsuario.DISTRIBUCION},
]

async def seed_users():
    async with AsyncSessionLocal() as db:
        for user_data in usuarios_data:
            result = await db.execute(select(Usuario).where(Usuario.codigo_empleado == user_data["codigo"]))
            existing_user = result.scalars().first()
            if not existing_user:
                new_user = Usuario(
                    codigo_empleado=user_data["codigo"],
                    nombre=user_data["nombre"],
                    rol=user_data["rol"],
                    cargo=user_data["cargo"],
                    area=user_data["area"],
                    password_hash=hash_password(user_data["codigo"])
                )
                db.add(new_user)
                print(f"Creado: {user_data['nombre']} ({user_data['codigo']})")
            else:
                print(f"Ya existe: {user_data['nombre']} ({user_data['codigo']})")
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_users())
