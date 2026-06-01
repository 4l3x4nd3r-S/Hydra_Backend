import uuid
from fastapi import UploadFile
from supabase import create_client

from app.core.config import settings


def get_supabase():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


async def upload_file(file: UploadFile, subfolder: str) -> str:
    ext = ""
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1]

    filename = f"{subfolder}/{uuid.uuid4()}{ext}"
    contents = await file.read()

    supabase = get_supabase()
    supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
        path=filename,
        file=contents,
        file_options={"content-type": file.content_type or "application/octet-stream"},
    )

    public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(filename)
    return public_url
