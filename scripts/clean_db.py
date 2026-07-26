import asyncio
import re
import aiohttp
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import random
from datetime import timedelta

# Set up imports for the app
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import AsyncSessionLocal
from app.models.orden_servicio import OrdenServicio
from app.models.reclamo import Reclamo

REAL_PROBLEMS = [
    "Rotura de tubería matriz en la esquina",
    "Fuga de agua constante en el medidor",
    "Atoro severo en la caja de registro principal",
    "Baja presión de agua en toda la cuadra",
    "Agua turbia con sedimentos en la conexión domiciliaria",
    "Hundimiento de pista por fuga subterránea",
    "Filtro de medidor obstruido con arena",
    "Válvula de compuerta atascada en posición cerrada",
]

REAL_SOLUTIONS = [
    "Se reemplazó tramo de tubería PVC de 4 pulgadas y se selló con pegamento especial.",
    "Se ajustaron conectores del medidor y se cambió empaquetadura.",
    "Se utilizó máquina desatoradora para limpiar la línea principal hasta el colector.",
    "Se purgó la línea y se calibró la válvula reductora de presión.",
    "Se realizó desfogue en grifo contra incendio cercano para limpiar sedimentos.",
    "Se reparó fuga, se rellenó con material de préstamo y se compactó.",
    "Se desarmó medidor, se limpió filtro y se volvió a instalar.",
    "Se lubricó y desbloqueó el vástago de la válvula, dejándola operativa.",
]

def is_test_data(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    
    # Palabras de prueba comunes
    if re.search(r'(test|prueba|asd|qwe|zxc|dess+|sss+)', text_lower):
        return True
    
    # Textos literales que son relleno
    if "descripci" in text_lower or "este es un reclamo" in text_lower or "formato 1" in text_lower:
        return True
        
    # 3 o más letras repetidas seguidas (ej: observacionessssss)
    if re.search(r'(.)\1{2,}', text_lower):
        return True
        
    # Texto muy corto (menor a 10 caracteres)
    if len(text.strip()) < 10 and len(text.strip()) > 0:
        return True
        
    return False

async def is_url_valid(session, url: str) -> bool:
    if not url or not url.startswith('http'):
        return False
    try:
        async with session.head(url, timeout=5) as response:
            return response.status < 400
    except Exception:
        return False

async def clean_db():
    async with aiohttp.ClientSession() as http_session:
        async with AsyncSessionLocal() as db:
            print("Buscando órdenes de servicio...")
            
            result = await db.execute(select(OrdenServicio).options(selectinload(OrdenServicio.reclamo)))
            ordenes = result.scalars().all()
            
            for os_obj in ordenes:
                needs_fix = False
                
                if is_test_data(os_obj.trabajo_ejecutado):
                    os_obj.trabajo_ejecutado = random.choice(REAL_SOLUTIONS)
                    needs_fix = True
                if is_test_data(os_obj.problemas):
                    os_obj.problemas = random.choice(REAL_PROBLEMS)
                    needs_fix = True
                if is_test_data(os_obj.soluciones):
                    os_obj.soluciones = random.choice(REAL_SOLUTIONS)
                    needs_fix = True
                if is_test_data(os_obj.comentarios_instrucciones):
                    os_obj.comentarios_instrucciones = "Revisar nivel de presión después de reparación."
                    needs_fix = True
                if is_test_data(os_obj.observaciones_gasfitero):
                    os_obj.observaciones_gasfitero = "Trabajo terminado sin inconvenientes."
                    needs_fix = True
                    
                if os_obj.reclamo:
                    r = os_obj.reclamo
                    r_fixed = False
                    if is_test_data(r.descripcion):
                        r.descripcion = random.choice(REAL_PROBLEMS)
                        r_fixed = True
                    if is_test_data(r.nombre_solicitante):
                        r.nombre_solicitante = "Juan Pérez"
                        r_fixed = True
                    if is_test_data(r.direccion):
                        r.direccion = "Av. Principal 123"
                        r_fixed = True

            print("Realizando limpieza de Reclamos...")
            res_reclamos = await db.execute(select(Reclamo))
            reclamos = res_reclamos.scalars().all()
            for r in reclamos:
                r_fixed = False
                if is_test_data(r.descripcion):
                    r.descripcion = random.choice(REAL_PROBLEMS)
                    r_fixed = True
                if is_test_data(r.nombre_solicitante):
                    r.nombre_solicitante = "Juan Pérez"
                    r_fixed = True
                if is_test_data(r.direccion):
                    r.direccion = "Av. Principal 123"
                    r_fixed = True

            await db.commit()
            print("Limpieza de strings adicionales finalizada.")

if __name__ == "__main__":
    asyncio.run(clean_db())
