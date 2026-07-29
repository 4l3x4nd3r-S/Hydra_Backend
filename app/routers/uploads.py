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
async def upload_evidencia(file: UploadFile = File(...)):
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
    db: AsyncSession = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
        
    files_data = []
    urls_guardadas = []
    
    try:
        for file in files:
            file_bytes = await file.read()
            
            # Guardar en Storage (backup original) con estructura de carpetas
            # Reemplazamos espacios por guiones bajos para las carpetas
            origen_limpio = origen.replace(' ', '_')
            unique_name = f"{uuid.uuid4()}_{file.filename}"
            ruta_completa_storage = f"dataloggers/{origen_limpio}/{fecha}/{unique_name}"
            
            if supabase:
                supabase.storage.from_(DATA_BUCKET).upload(
                    file=file_bytes,
                    path=ruta_completa_storage,
                    file_options={"content-type": file.content_type}
                )
                url = supabase.storage.from_(DATA_BUCKET).get_public_url(ruta_completa_storage)
                urls_guardadas.append(url)
            
            files_data.append({
                "filename": file.filename,
                "content": file_bytes
            })
            
        # Llamar al procesador
        resultado = await process_dataloggers(files_data, db)
        resultado["backup_urls"] = urls_guardadas
        
        return JSONResponse(status_code=200, content=resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando dataloggers: {str(e)}")
@router.get("/reclamos/status/{job_id}", summary="Ver estado de subida de reclamos")
async def get_reclamos_upload_status(job_id: str):
    job = upload_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return JSONResponse(status_code=200, content=job)

@router.post("/reclamos", summary="Subir y procesar archivo de Reclamos")
async def upload_reclamos(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
        
    try:
        file_bytes = await file.read()
        
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
