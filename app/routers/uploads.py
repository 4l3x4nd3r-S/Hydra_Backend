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
        raise HTTPException(status_code=500, detail=f"Error al subir archivo de reclamos: {str(e)}")
