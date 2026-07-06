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
