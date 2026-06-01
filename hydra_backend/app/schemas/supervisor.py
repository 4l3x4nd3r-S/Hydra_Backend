from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.orden_trabajo import PrioridadOT


class TecnicoResponse(BaseModel):
    id: int
    dni: str
    nombre: str
    cuadrilla_nombre: Optional[str] = None

    model_config = {"from_attributes": True}


class CrearOTRequest(BaseModel):
    sensor_id: Optional[str] = None
    sector_id: Optional[int] = None
    asignado_a: int
    prioridad: PrioridadOT
    alerta_id: Optional[int] = None


class OTSupervisorResponse(BaseModel):
    id: int
    sensor_id: Optional[str] = None
    sector_id: Optional[int] = None
    asignado_a: Optional[int] = None
    tecnico_nombre: Optional[str] = None
    estado: str
    prioridad: str
    created_at: datetime
    started_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
