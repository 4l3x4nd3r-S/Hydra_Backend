import os
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client, Client

from app.core.config import settings
from app.core.database import get_db
from app.services.datalogger_processor import process_dataloggers
from app.services.reclamo_processor import process_reclamos_background, upload_jobs
from app.core.security import get_current_user
from app.models.usuario import Usuario

router = APIRouter(prefix="/uploads", tags=["Uploads"])

supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
# Usaremos el bucket por defecto para subidas generales
DEFAULT_BUCKET = "evidencias"
# Usaremos el nuevo bucket para archivos de datos
DATA_BUCKET = "archivos_origen"

supabase: Client | None = None
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

def upload_to_supabase(file_bytes: bytes, filename: str, content_type: str, bucket: str) -> str:
    """Helper para subir archivo a Supabase Storage y retornar su URL pública."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase no está configurado")
        
    file_ext = os.path.splitext(filename)[1] if filename else ""
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    supabase.storage.from_(bucket).upload(
        file=file_bytes,
        path=unique_filename,
        file_options={"content-type": content_type or "application/octet-stream"}
    )
    return supabase.storage.from_(bucket).get_public_url(unique_filename)


@router.post("/evidencias", summary="Subir imagen de evidencia (Órdenes de Servicio)")
async def upload_evidencia(
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Sube una imagen de evidencia para una orden de servicio. 
    (Ej. foto del problema antes de reparar, o foto de la solución terminada).
    El archivo se guarda en el bucket 'evidencias' y retorna la URL pública.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validar que sea una imagen (opcional pero recomendado)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    
    try:
        file_bytes = await file.read()
        public_url = upload_to_supabase(file_bytes, file.filename, file.content_type, DEFAULT_BUCKET)
        return JSONResponse(status_code=200, content={"url": public_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dataloggers", summary="Subir y procesar archivos de Dataloggers")
async def upload_dataloggers(
    files: List[UploadFile] = File(...),
    origen: str = Form(...),
    fecha: str = Form(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
        
    files_data = []
    urls_guardadas = []
    
    try:
        # 1. Leer archivos a memoria
        for file in files:
            file_bytes = await file.read()
            files_data.append({
                "filename": file.filename,
                "content": file_bytes,
                "content_type": file.content_type
            })
            
        # 2. Llamar al procesador PRIMERO (Si hay duplicados o fechas inválidas, lanzará error y se detiene aquí)
        resultado = await process_dataloggers(files_data, db, origen, fecha)
        
        # 3. Solo si la base de datos aceptó los datos y no fue omitido, guardamos los Excels en Storage
        archivos_procesados = resultado.get("archivos_procesados", [])
        
        for file_data in files_data:
            if file_data["filename"] not in archivos_procesados:
                continue # Omitir subir archivos que ya existían en BD o que fueron filtrados
                
            origen_limpio = origen.replace(' ', '_')
            unique_name = f"{uuid.uuid4()}_{file_data['filename']}"
            ruta_completa_storage = f"dataloggers/{origen_limpio}/{fecha}/{unique_name}"
            
            if supabase:
                supabase.storage.from_(DATA_BUCKET).upload(
                    file=file_data["content"],
                    path=ruta_completa_storage,
                    file_options={"content-type": file_data["content_type"]}
                )
                url = supabase.storage.from_(DATA_BUCKET).get_public_url(ruta_completa_storage)
                urls_guardadas.append(url)
                
        resultado["backup_urls"] = urls_guardadas
        return JSONResponse(status_code=200, content=resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando dataloggers: {str(e)}")
@router.get("/reclamos/status/{job_id}", summary="Ver estado de subida de reclamos")
async def get_reclamos_upload_status(
    job_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    job = upload_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return JSONResponse(status_code=200, content=job)

@router.post("/reclamos", summary="Subir y procesar archivo de Reclamos")
async def upload_reclamos(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
        
    try:
        file_bytes = await file.read()
        
        # Validación sincrónica rápida para evitar subir duplicados al Storage
        import pandas as pd
        import io
        from sqlalchemy import select
        from app.models.reclamo_historico import ReclamoHistorico
        
        try:
            # Leer solo las primeras filas para ser súper rápidos, pero en un thread separado para no bloquear el Event Loop
            complaints_columns = ['N° Reclamo', 'Cod Cliente']
            import asyncio
            loop = asyncio.get_event_loop()
            df_check = await loop.run_in_executor(
                None,
                lambda c=file_bytes, cols=complaints_columns: pd.read_excel(io.BytesIO(c), skiprows=10, usecols=cols, nrows=5)
            )
            
            if not df_check.empty:
                primer_reclamo = str(df_check.iloc[0]['N° Reclamo']).strip()
                if primer_reclamo.endswith('.0'): primer_reclamo = primer_reclamo[:-2]
                
                if primer_reclamo == '00000' or primer_reclamo.lower() == 'nan' or primer_reclamo == '' or primer_reclamo == 'None':
                    primer_reclamo = None
                else:
                    primer_reclamo = primer_reclamo.zfill(5)
                
                primer_suministro = str(df_check.iloc[0]['Cod Cliente']).strip()
                if primer_suministro.endswith('.0'): primer_suministro = primer_suministro[:-2]
                
                if primer_suministro == '0000000' or primer_suministro.lower() == 'nan' or primer_suministro == '' or primer_suministro == 'None':
                    primer_suministro = None
                else:
                    primer_suministro = primer_suministro.zfill(7)
                
                # Buscar si ya existe este reclamo en la BD
                if primer_reclamo:
                    result = await db.execute(
                        select(ReclamoHistorico).where(ReclamoHistorico.codigo_solicitud == primer_reclamo)
                    )
                    if result.scalars().first():
                        # Si ya existe, abortamos TODO inmediatamente antes de guardar en Storage
                        return JSONResponse(status_code=400, content={
                            "detail": "Este archivo de reclamos ya fue subido anteriormente (se detectaron reclamos duplicados)."
                        })
        except Exception as e:
            # Si el Excel tiene un formato inválido, fallará aquí, pero lo dejamos pasar 
            # para que el processor en background lo reporte correctamente.
            pass
            
        # Subir a Storage
        backup_url = None
        if supabase:
            unique_name = f"reclamos/{uuid.uuid4()}_{file.filename}"
            supabase.storage.from_(DATA_BUCKET).upload(
                file=file_bytes,
                path=unique_name,
                file_options={"content-type": file.content_type}
            )
            backup_url = supabase.storage.from_(DATA_BUCKET).get_public_url(unique_name)
            
        # Programar tarea en segundo plano para procesar reclamos
        job_id = str(uuid.uuid4())
        upload_jobs[job_id] = {"status": "queued", "total": 0, "processed": 0, "error": None}
        background_tasks.add_task(process_reclamos_background, file_bytes, file.filename, job_id)
        
        return JSONResponse(status_code=202, content={
            "message": "Archivo recibido correctamente. El procesamiento de reclamos se está ejecutando en segundo plano.",
            "job_id": job_id,
            "backup_url": backup_url
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al subir archivo de reclamos: {str(e)}")
