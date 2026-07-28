import asyncio
import io
import pandas as pd
import requests
import yaml
from pathlib import Path
from datetime import datetime

from app.core.database import AsyncSessionLocal
from app.models.reclamo import Reclamo

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
    """Retorna (latitud, longitud) usando Nominatim"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        location = ', PUERTO MALDONADO, MADRE DE DIOS, PERÚ'
        params = {
            "q": address + location,
            "format": "json",
            "addressdetails": 1,
            "limit": 1
        }
        headers = {
            "User-Agent": "HydraBackend/2.0"
        }
        # Hacer petición bloqueante de requests en un thread separado para no bloquear asyncio
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, lambda: requests.get(url, params=params, headers=headers, timeout=10))
        
        if r.status_code == 200:
            data = r.json()
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
    return None, None

async def process_reclamos_background(content: bytes, filename: str):
    """
    Procesador en segundo plano para reclamos.
    """
    print(f"Iniciando procesamiento de reclamos para {filename}...")
    try:
        complaints_columns = ['N° Reclamo', 'Cod Cliente', 'Dirección', 'Fecha Reclamo', 'Tipo Reclamo']
        
        # Leer excel
        df = pd.read_excel(io.BytesIO(content), skiprows=10, usecols=complaints_columns)
        
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
        
        df.columns = ['complaint_number', 'client_code', 'address', 'date_complaint', 'type_complaint']
        
        # Procesar y geocodificar uno por uno
        registros_a_insertar = []
        
        # Obtenemos las direcciones únicas para minimizar llamadas a la API
        direcciones_unicas = df['address'].dropna().unique()
        mapa_coordenadas = {}
        
        print(f"Geocodificando {len(direcciones_unicas)} direcciones únicas. Esto tomará aproximadamente {len(direcciones_unicas)} segundos...")
        for address in direcciones_unicas:
            lat, lon = await geocode_address(address)
            mapa_coordenadas[address] = (lat, lon)
            # Respetar la política de Nominatim (1 request por segundo)
            await asyncio.sleep(1.1)
            
        # Preparar inserciones
        for _, row in df.iterrows():
            address = str(row['address'])
            lat, lon = mapa_coordenadas.get(address, (None, None))
            
            # Limpiar codigos para que cumplan con regex si es posible
            num_reclamo = str(row['complaint_number']).strip()
            if num_reclamo.endswith('.0'): num_reclamo = num_reclamo[:-2]
            if len(num_reclamo) != 5 or num_reclamo == '00000':
                num_reclamo = None
                
            cod_cliente = str(row['client_code']).strip()
            if cod_cliente.endswith('.0'): cod_cliente = cod_cliente[:-2]
            if len(cod_cliente) != 7 or cod_cliente == '0000000':
                cod_cliente = None
            
            fecha = row['date_complaint']
            if pd.isnull(fecha):
                fecha = datetime.now()
                
            reclamo = Reclamo(
                codigo_solicitud=num_reclamo,
                numero_suministro=cod_cliente,
                direccion=address,
                fecha_registro=fecha,
                tipo_problema=str(row['type_complaint']) if pd.notnull(row['type_complaint']) else None,
                latitud=lat,
                longitud=lon,
                estado="PENDIENTE", # Estado por defecto
                canal_entrada="ARCHIVO_EXCEL"
            )
            registros_a_insertar.append(reclamo)
            
        if registros_a_insertar:
            async with AsyncSessionLocal() as db:
                db.add_all(registros_a_insertar)
                await db.commit()
                print(f"[{filename}] Se insertaron {len(registros_a_insertar)} reclamos correctamente.")
        else:
            print(f"[{filename}] No se encontraron registros válidos para insertar.")
            
    except Exception as e:
        print(f"Error procesando el archivo de reclamos {filename} en background: {e}")
