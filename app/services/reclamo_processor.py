import asyncio
import io
import pandas as pd
import requests
import yaml
from pathlib import Path
from datetime import datetime

from app.core.database import AsyncSessionLocal
from app.models.reclamo_historico import ReclamoHistorico

# Si se cuenta con un yaml real en el sistema de archivos:
# REEMPLAZOS_PATH = Path('C:/Users/ALEXANDER_SUNI/Documents/ALEXANDERSUNI/DATA/datathon/data/utils/reemplazos.yaml')

# Para propósitos de este processor, si el archivo yaml no existe en el repo de Hydra, 
# podemos definir reemplazos comunes aquí, o intentar leer el YAML original.
def get_reemplazos() -> dict:
    # Intentamos leer el archivo de la datathon si existe localmente
    yaml_path = Path(r'C:\Users\ALEXANDER_SUNI\Documents\ALEXANDERSUNI\DATA\datathon\data\utils\reemplazos.yaml')
    if yaml_path.exists():
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('reemplazos', {})
    return {}

async def geocode_address(address: str) -> tuple:
    """Retorna (latitud, longitud) usando Google Maps Geocoding API"""
    from app.core.config import settings
    if not settings.GOOGLE_MAPS_API_KEY:
        print("Advertencia: No hay GOOGLE_MAPS_API_KEY configurada.")
        return None, None
        
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        location = ', PUERTO MALDONADO, MADRE DE DIOS, PERÚ'
        params = {
            "address": address + location,
            "key": settings.GOOGLE_MAPS_API_KEY
        }
        
        # Hacer petición bloqueante de requests en un thread separado para no bloquear asyncio
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, lambda: requests.get(url, params=params, timeout=10))
        
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'OK' and data.get('results'):
                location_data = data['results'][0]['geometry']['location']
                return float(location_data['lat']), float(location_data['lng'])
            else:
                print(f"No se encontraron coordenadas para {address}: {data.get('status')}")
        else:
            print(f"Error de API para {address}: {r.status_code}")
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
    return None, None

from typing import Dict, Any

# Diccionario global para rastrear el progreso de subidas
upload_jobs: Dict[str, Dict[str, Any]] = {}

async def process_reclamos_background(content: bytes, filename: str, job_id: str):
    """
    Procesador en segundo plano para reclamos.
    """
    upload_jobs[job_id] = {"status": "starting", "total": 0, "processed": 0, "error": None}
    print(f"Iniciando procesamiento de reclamos para {filename} (Job: {job_id})...")
    try:
        complaints_columns = ['N° Reclamo', 'Cod Cliente', 'Dirección', 'Fecha Reclamo', 'Tipo Reclamo']
        # Leer excel en un thread separado para no bloquear el servidor
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda c=content, cols=complaints_columns: pd.read_excel(io.BytesIO(c), skiprows=10, usecols=cols)
        )
        
        # Transformar fechas
        df['Fecha Reclamo'] = pd.to_datetime(df['Fecha Reclamo'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
        
        # Transformar dirección
        df['Dirección'] = df['Dirección'].astype(str).str.upper()
        
        reemplazos = get_reemplazos()
        if reemplazos:
            df['Dirección'] = df['Dirección'].replace(reemplazos, regex=True)
            
        df['Dirección'] = df['Dirección'].str.strip('.')
        df['Dirección'] = df['Dirección'].str.strip()
        df['Dirección'] = df['Dirección'].str.replace('  ', ' ', regex=True)
        
        upload_jobs[job_id]["total"] = len(df)
        upload_jobs[job_id]["status"] = "processing"
        
        print(f"Procesando {len(df)} reclamos en lotes...")
        mapa_coordenadas = {}
        registros_a_insertar = []
        batch_size = 100  # Insertar en base de datos cada 100 filas
        total_insertados = 0
        
        for _, row in df.iterrows():
            address = str(row['Dirección'])
            
            # Geocodificar solo si no lo tenemos en caché
            if address not in mapa_coordenadas:
                lat, lon = await geocode_address(address)
                mapa_coordenadas[address] = (lat, lon)
                await asyncio.sleep(0.1)  # Respetar límite de la API
            else:
                lat, lon = mapa_coordenadas[address]
                
            num_reclamo = str(row['N° Reclamo']).strip()
            if num_reclamo.endswith('.0'): num_reclamo = num_reclamo[:-2]
            if num_reclamo == '00000' or num_reclamo.lower() == 'nan' or num_reclamo == '':
                num_reclamo = None
            elif num_reclamo != 'None':
                num_reclamo = num_reclamo.zfill(5)
            else:
                num_reclamo = None
                
            cod_cliente = str(row['Cod Cliente']).strip()
            if cod_cliente.endswith('.0'): cod_cliente = cod_cliente[:-2]
            if cod_cliente == '0000000' or cod_cliente.lower() == 'nan' or cod_cliente == '':
                cod_cliente = None
            elif cod_cliente != 'None':
                cod_cliente = cod_cliente.zfill(7)
            else:
                cod_cliente = None
            
            fecha = row['Fecha Reclamo']
            if pd.isnull(fecha):
                fecha = datetime.now()
                
            reclamo_dict = {
                "codigo_solicitud": num_reclamo,
                "numero_suministro": cod_cliente,
                "direccion": address,
                "fecha_registro": fecha,
                "tipo_problema": str(row['Tipo Reclamo']) if pd.notnull(row['Tipo Reclamo']) else None,
                "latitud": lat,
                "longitud": lon,
                "estado": "HISTORICO"
            }
            registros_a_insertar.append(reclamo_dict)
            upload_jobs[job_id]["processed"] += 1
            
            # Si llegamos al tamaño del lote, guardamos en la base de datos
            if len(registros_a_insertar) >= batch_size:
                async with AsyncSessionLocal() as db:
                    from sqlalchemy.dialects.postgresql import insert as pg_insert
                    stmt = pg_insert(ReclamoHistorico).values(registros_a_insertar)
                    stmt = stmt.on_conflict_do_nothing(constraint="uq_reclamo_historico")
                    await db.execute(stmt)
                    await db.commit()
                total_insertados += len(registros_a_insertar) # Podría ser menos si hubo duplicados, pero es el total procesado
                registros_a_insertar = []
                
        # Insertar los registros restantes que no alcanzaron a formar un lote completo
        if registros_a_insertar:
            async with AsyncSessionLocal() as db:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                stmt = pg_insert(ReclamoHistorico).values(registros_a_insertar)
                stmt = stmt.on_conflict_do_nothing(constraint="uq_reclamo_historico")
                await db.execute(stmt)
                await db.commit()
            total_insertados += len(registros_a_insertar)
            
        print(f"[{filename}] Se procesaron {total_insertados} reclamos correctamente en lotes (se omitieron duplicados silenciosamente).")
        upload_jobs[job_id]["status"] = "completed"
            
    except Exception as e:
        upload_jobs[job_id]["status"] = "error"
        upload_jobs[job_id]["error"] = str(e)
        print(f"Error procesando el archivo de reclamos {filename} en background: {e}")
