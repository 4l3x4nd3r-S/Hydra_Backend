import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from supabase import create_client, Client
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["Uploads"])

supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
bucket_name = "evidencias"

supabase: Client | None = None
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

@router.post("", summary="Subir un archivo")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase no está configurado")
    
    try:
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        file_bytes = await file.read()
        
        res = supabase.storage.from_(bucket_name).upload(
            file=file_bytes,
            path=unique_filename,
            file_options={"content-type": file.content_type or "application/octet-stream"}
        )
        
        public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
        
        return JSONResponse(status_code=200, content={"url": public_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
