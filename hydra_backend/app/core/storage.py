import logging
import uuid

from fastapi import UploadFile
from supabase import create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_supabase():
    # Usar service_role key si está disponible (tiene permisos de escritura en Storage)
    # Si no, usar la key anon (puede fallar si el bucket tiene RLS activado)
    key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
    return create_client(settings.SUPABASE_URL, key)


async def upload_file(file: UploadFile, subfolder: str) -> str:
    ext = ""
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1]

    filename = f"{subfolder}/{uuid.uuid4()}{ext}"
    contents = await file.read()

    supabase = get_supabase()
    response = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
        path=filename,
        file=contents,
        file_options={
            "content-type": file.content_type or "application/octet-stream",
            "upsert": "true",
        },
    )

    if hasattr(response, "error") and response.error:
        logger.error("Supabase Storage error: %s", response.error)
        raise Exception(f"Storage upload failed: {response.error}")

    public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(filename)
    logger.info("Archivo subido: %s", public_url)
    return public_url
