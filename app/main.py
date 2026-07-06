import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exception_handlers import value_error_handler, unhandled_exception_handler
from app.routers import auth, usuarios, sectores, puntos_presion, registros_presion, reclamos, cuadrillas, elementos_red, ordenes_servicio, supervisor, uploads

setup_logging()

if not os.path.exists("uploads"):
    os.makedirs("uploads")

app = FastAPI(
    title="Hydra API",
    description="Sistema de detección y ruteo de fugas - EMAPAT S.A.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(usuarios.router, prefix="/api/v1")
app.include_router(sectores.router, prefix="/api/v1")
app.include_router(puntos_presion.router, prefix="/api/v1")
app.include_router(registros_presion.router, prefix="/api/v1")
app.include_router(reclamos.router, prefix="/api/v1")
app.include_router(cuadrillas.router, prefix="/api/v1")
app.include_router(elementos_red.router, prefix="/api/v1")
app.include_router(ordenes_servicio.router, prefix="/api/v1")
app.include_router(supervisor.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/health", tags=["Sistema"], summary="Estado del servidor")
@app.head("/health", tags=["Sistema"], summary="Estado del servidor (UptimeRobot)")
async def health_check():
    return {"status": "ok", "service": "Hydra"}
