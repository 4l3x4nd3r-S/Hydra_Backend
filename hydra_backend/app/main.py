from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.routers import auth, ot, analytics, supervisor, sensores, usuarios

app = FastAPI(
    title="Hydra API",
    description="Sistema de detección y ruteo de fugas - EMAPAT S.A.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOADS_DIR), name="uploads")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(ot.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(supervisor.router, prefix="/api/v1")
app.include_router(sensores.router, prefix="/api/v1")
app.include_router(usuarios.router, prefix="/api/v1")


@app.get("/health", tags=["Sistema"], summary="Estado del servidor")
async def health_check():
    return {"status": "ok", "service": "Hydra"}
