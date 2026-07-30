import io
import pandas as pd
from typing import List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.punto_presion import PuntoPresion
from app.models.registro_presion import RegistroPresion

async def process_dataloggers(
    files_data: List[dict],
    db: AsyncSession,
    origen: str,
    fecha_esperada: str = None
) -> dict:
    """
    Procesa un lote de archivos Excel de dataloggers subidos desde el frontend.
    `files_data` debe ser una lista de dicts: {"filename": str, "content": bytes}
    `fecha_esperada` es el mes indicado por el usuario (ej. "2024-01") para validar.
    """
    lista_dataframes = []
    
    # 1. Procesar cada archivo en memoria con pandas
    for file_info in files_data:
        filename = file_info["filename"]
        content = file_info["content"]
        
        try:
            # Extraer el punto de presión del nombre del archivo (ej. "...P-32.xlsx" -> "P-32")
            # Se asume que el formato siempre termina en P-XX.xlsx o P-XXX.xlsx
            # Una forma más robusta con regex:
            import re
            match = re.search(r'(P-\d+)', filename.upper())
            if not match:
                raise ValueError(f"No se pudo extraer el código del punto de presión del archivo {filename}")
            
            codigo_punto = match.group(1)
            
            # Leer el excel (saltando la cabecera) de forma asíncrona para no bloquear el servidor
            import asyncio
            loop = asyncio.get_event_loop()
            df_temp = await loop.run_in_executor(
                None,
                lambda c=content: pd.read_excel(io.BytesIO(c), sheet_name=1, skiprows=6)
            )
            
            # Quitar la primera columna (índice interno o irrelevante)
            df_temp = df_temp.iloc[:, 1:]
            
            # Limpieza como en el script original
            if 'Alarmas' in df_temp.columns:
                df_temp.drop(columns=['Alarmas'], inplace=True)
                
            if 'Presión (psi)' in df_temp.columns:
                df_temp['Presión (psi)'] = df_temp['Presión (psi)'] / 1.422
                df_temp.rename(columns={'Presión (psi)': 'Presión (mH2O)'}, inplace=True)
                
            # Validar que tengamos las 3 columnas esperadas (Tiempo, Temperatura, Presión)
            # En caso que falte la temperatura o cambie el orden, asumimos el orden:
            # time, temperature, pressure
            if len(df_temp.columns) >= 3:
                df_temp = df_temp.iloc[:, :3]
                df_temp.columns = ['time', 'temperature', 'pressure']
            else:
                # Si solo hay tiempo y presión
                df_temp.columns = ['time', 'pressure']
                df_temp['temperature'] = None
                
            df_temp['codigo_punto'] = codigo_punto
            df_temp['filename'] = filename
            
            # Limpiar filas nulas en tiempo
            df_temp = df_temp.dropna(subset=['time'])
            
            # Validar que la fecha de los datos coincida con la fecha indicada por el supervisor
            if fecha_esperada and not df_temp.empty:
                primer_tiempo = df_temp['time'].iloc[0]
                if isinstance(primer_tiempo, str):
                    try:
                        primer_tiempo = datetime.strptime(primer_tiempo, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass # Si el formato es distinto, omitir esta validación estricta para evitar bloqueos
                
                if isinstance(primer_tiempo, datetime) or hasattr(primer_tiempo, 'year'):
                    try:
                        exp_year, exp_month = map(int, fecha_esperada.split("-"))
                        if primer_tiempo.year != exp_year or primer_tiempo.month != exp_month:
                            mes_real = f"{primer_tiempo.year}-{primer_tiempo.month:02d}"
                            raise ValueError(f"Incongruencia: El archivo {filename} contiene datos de {mes_real}, pero se intentó subir en la carpeta {fecha_esperada}.")
                    except ValueError as ve:
                        if "Incongruencia:" in str(ve):
                            raise ve
            
            lista_dataframes.append(df_temp)
            
        except Exception as e:
            print(f"Error procesando {filename}: {e}")
            raise ValueError(f"Error procesando {filename}: {str(e)}")

    if not lista_dataframes:
        return {"success": False, "message": "No se encontraron datos válidos para procesar."}

    # Unir todo
    df_consolidado = pd.concat(lista_dataframes, ignore_index=True)
    
    # 2. Mapear códigos de punto de presión a sus objetos en la base de datos
    codigos_unicos = df_consolidado['codigo_punto'].unique().tolist()
    
    result = await db.execute(
        select(PuntoPresion)
        .where(
            PuntoPresion.codigo_punto.in_(codigos_unicos),
            PuntoPresion.origen == origen
        )
    )
    puntos_db = result.scalars().all()
    mapa_puntos = {p.codigo_punto: p for p in puntos_db}
    
    # Identificar si hay puntos que no existen en la BD
    puntos_faltantes = [cod for cod in codigos_unicos if cod not in mapa_puntos]
    if puntos_faltantes:
        raise ValueError(f"Los siguientes puntos de presión no existen en la base de datos: {puntos_faltantes}")

    # 3. Preparar los registros para inserción masiva
    registros_a_insertar = []
    for _, row in df_consolidado.iterrows():
        try:
            # Intentar parsear el tiempo
            if isinstance(row['time'], str):
                fecha_hora = datetime.strptime(row['time'], '%Y-%m-%d %H:%M:%S')
            else:
                fecha_hora = row['time'] # Si ya es un objeto datetime o timestamp
                
            punto_obj = mapa_puntos[row['codigo_punto']]
                
            registros_a_insertar.append(
                RegistroPresion(
                    punto_presion_id=punto_obj.id,
                    fecha_hora=fecha_hora,
                    presion_mca=float(row['pressure']),
                    temperatura_c=float(row['temperature']) if pd.notnull(row['temperature']) else None,
                    zona=punto_obj.zona,
                    origen=punto_obj.origen
                )
            )
        except Exception as e:
            print(f"Error en fila: {row} - {e}")
            continue

    from sqlalchemy.dialects.postgresql import insert as pg_insert

    # 4. Insertar en base de datos (con ON CONFLICT DO NOTHING)
    if registros_a_insertar:
        valores_a_insertar = []
        for r in registros_a_insertar:
            valores_a_insertar.append({
                "punto_presion_id": r.punto_presion_id,
                "fecha_hora": r.fecha_hora,
                "presion_mca": r.presion_mca,
                "temperatura_c": r.temperatura_c,
                "zona": r.zona,
                "origen": r.origen
            })
            
        try:
            # Insertar por lotes para evitar el límite de parámetros de Postgres
            batch_size = 5000
            for i in range(0, len(valores_a_insertar), batch_size):
                batch = valores_a_insertar[i:i + batch_size]
                stmt = pg_insert(RegistroPresion).values(batch)
                stmt = stmt.on_conflict_do_nothing(constraint="uq_punto_timestamp")
                await db.execute(stmt)
                
            await db.commit()
            return {
                "success": True, 
                "message": f"Se procesaron {len(valores_a_insertar)} registros correctamente (omitiendo duplicados automáticamente).",
                "inserted": len(valores_a_insertar)
            }
        except Exception as e:
            await db.rollback()
            raise ValueError(f"Error al guardar en la base de datos: {str(e)}")
            
    return {"success": False, "message": "No hay registros para insertar"}
