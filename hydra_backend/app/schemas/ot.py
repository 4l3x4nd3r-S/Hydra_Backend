from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class UbicacionGPS(BaseModel):
    lat: float
    lon: float


class OTAsignadaResponse(BaseModel):
    id: int
    sensor_id: Optional[str]
    point_id: Optional[str]
    prioridad: str
    estado: str
    created_at: datetime
    ubicacion_estimada: Optional[UbicacionGPS]

    model_config = {"from_attributes": True}


class OTIniciadaResponse(BaseModel):
    message: str
    started_at: datetime


class ControlPresionResponse(BaseModel):
    ot_id: int
    sensor_id: str
    presion_actual_mca: float
    presion_recuperada: bool
    mensaje: str


class OTCerradaResponse(BaseModel):
    ot_id: int
    estado: str
    closed_at: datetime
    message: str
