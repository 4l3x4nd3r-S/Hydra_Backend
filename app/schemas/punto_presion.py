from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CrearPuntoPresionRequest(BaseModel):
    codigo_punto: str
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    sector_id: Optional[int] = None


class ActualizarPuntoPresionRequest(BaseModel):
    codigo_punto: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    sector_id: Optional[int] = None


class PuntoPresionResponse(BaseModel):
    id: int
    codigo_punto: str
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    sector_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class MetricasMes(BaseModel):
    year: int
    month: int
    presion_min: Optional[float] = None
    presion_max: Optional[float] = None
    presion_prom: Optional[float] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    temp_prom: Optional[float] = None

class HistorialPuntoResponse(BaseModel):
    codigo_punto: str
    metricas: list[MetricasMes]
